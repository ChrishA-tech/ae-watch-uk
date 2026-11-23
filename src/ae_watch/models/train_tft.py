"""PyTorch Multi-Horizon Sequence & Quantile Forecasting Architecture.

Implements a Temporal Sequence Model with Multi-Head Self-Attention and Gated Residual Networks.
Accelerated on Apple Silicon MPS backend with deterministic CPU fallback.
Predicts P10, P50, and P90 quantile breach rates.
Author: CHRISH PEP FELIX A
"""

import os
from typing import Any

import mlflow

os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from ae_watch.models.train_gbdt import (
    FEATURE_COLUMNS,
    generate_expanding_window_splits,
    load_dataset_from_db,
)
from ae_watch.utils.logger import logger


def get_optimal_torch_device() -> torch.device:
    """Detect and select Apple Silicon MPS acceleration or fallback to CPU."""
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        try:
            # Smoke test MPS tensor allocation
            t = torch.zeros(1, device="mps")
            del t
            return torch.device("mps")
        except (RuntimeError, ValueError) as exc:
            logger.warning("mps_initialization_failed_falling_back_to_cpu", error=str(exc))
    return torch.device("cpu")


class QuantilePinballLoss(nn.Module):
    """Pinball loss for multi-quantile regression (P10, P50, P90)."""

    def __init__(self, quantiles: tuple[float, ...] = (0.10, 0.50, 0.90)):
        super().__init__()
        self.quantiles = quantiles

    def forward(self, preds: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        losses = []
        for i, q in enumerate(self.quantiles):
            error = target - preds[:, i : i + 1]
            loss = torch.max(q * error, (q - 1.0) * error)
            losses.append(loss)
        return torch.mean(torch.cat(losses, dim=1))


class GatedResidualNetwork(nn.Module):
    """Gated Residual Network (GRN) building block for Temporal Fusion."""

    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.elu = nn.ELU()
        self.fc2 = nn.Linear(dim, dim)
        self.gate = nn.Linear(dim, dim)
        self.sigmoid = nn.Sigmoid()
        self.norm = nn.LayerNorm(dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        h = self.elu(self.fc1(x))
        h = self.dropout(self.fc2(h))
        g = self.sigmoid(self.gate(x))
        return self.norm(residual + g * h)


class TemporalFusionNetwork(nn.Module):
    """Multi-Horizon Temporal Sequence Network with Self-Attention and Quantile Output Heads."""

    def __init__(
        self, input_dim: int, hidden_dim: int = 64, num_heads: int = 4, num_quantiles: int = 3
    ):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.grn1 = GatedResidualNetwork(hidden_dim)
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=num_heads, batch_first=True
        )
        self.grn2 = GatedResidualNetwork(hidden_dim)
        self.quantile_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, num_quantiles),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Support both 2D (batch_size, input_dim) and 3D (batch_size, seq_len, input_dim)
        if x.dim() == 2:
            h = self.input_proj(x).unsqueeze(1)
        else:
            h = self.input_proj(x)
        h = self.grn1(h)
        attn_out, _ = self.attention(h, h, h)
        h = self.grn2(h + attn_out)
        if h.dim() == 3 and h.shape[1] == 1:
            h = h.squeeze(1)
        elif h.dim() == 3:
            h = h.mean(dim=1)
        return self.quantile_head(h)


class PyTorchTFTTrainer:
    """Trainer orchestrating training on MPS/CPU with expanding temporal cross-validation."""

    def __init__(self, tracking_uri: str = "file:./mlruns"):
        self.device = get_optimal_torch_device()
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment("ae_watch_uk_pytorch_tft")
        logger.info("pytorch_device_selected", device=str(self.device))

    def train_epoch(
        self,
        model: nn.Module,
        loader: DataLoader,
        optimizer: torch.optim.Optimizer,
        criterion: nn.Module,
    ) -> float:
        model.train()
        total_loss = 0.0
        for bx, by in loader:
            bx, by = bx.to(self.device), by.to(self.device)
            optimizer.zero_grad()
            preds = model(bx)
            loss = criterion(preds, by)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())
        return total_loss / len(loader)

    def evaluate(
        self,
        model: nn.Module,
        X_val: np.ndarray,
        y_val: np.ndarray,
        criterion: nn.Module,
    ) -> dict[str, float]:
        model.eval()
        with torch.no_grad():
            bx = torch.tensor(X_val, dtype=torch.float32, device=self.device)
            by = torch.tensor(y_val, dtype=torch.float32, device=self.device).unsqueeze(1)
            preds = model(bx)
            loss = float(criterion(preds, by).item())

            # Move to CPU for metrics
            preds_np = preds.cpu().numpy()
            p10, p50, p90 = preds_np[:, 0], preds_np[:, 1], preds_np[:, 2]

            # Quantile Monotonicity
            p50 = np.maximum(p10, p50)
            p90 = np.maximum(p50, p90)

            mae = float(np.mean(np.abs(y_val - p50)))
            rmse = float(np.sqrt(np.mean((y_val - p50) ** 2)))
            coverage = float(np.mean((y_val >= p10) & (y_val <= p90)))

            return {
                "loss": loss,
                "mae": mae,
                "rmse": rmse,
                "coverage_80pct": coverage,
            }

    def run_training_pipeline(self, epochs: int = 15, batch_size: int = 64) -> dict[str, Any]:
        """Train TFT architecture across expanding-window temporal splits."""
        df = load_dataset_from_db()
        X_raw = df[FEATURE_COLUMNS].fillna(0.0).to_numpy()
        y_raw = df["target_breach_rate_horizon_7d"].to_numpy()

        splits = generate_expanding_window_splits(df)
        logger.info("tft_expanding_splits", count=len(splits), device=str(self.device))

        fold_metrics = []

        with mlflow.start_run(run_name="pytorch_tft_multi_horizon"):
            mlflow.log_param("author", "CHRISH PEP FELIX A")
            mlflow.log_param("device", str(self.device))
            mlflow.log_param("epochs", epochs)
            mlflow.log_param("batch_size", batch_size)

            criterion = QuantilePinballLoss(quantiles=(0.10, 0.50, 0.90))

            for fold_idx, (train_idx, val_idx) in enumerate(splits):
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X_raw[train_idx])
                X_vl = scaler.transform(X_raw[val_idx])
                y_tr, y_vl = y_raw[train_idx], y_raw[val_idx]

                train_dataset = TensorDataset(
                    torch.tensor(X_tr, dtype=torch.float32),
                    torch.tensor(y_tr, dtype=torch.float32).unsqueeze(1),
                )
                train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

                model = TemporalFusionNetwork(input_dim=len(FEATURE_COLUMNS), hidden_dim=64).to(
                    self.device
                )
                optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)

                for _ in range(epochs):
                    self.train_epoch(model, train_loader, optimizer, criterion)

                eval_res = self.evaluate(model, X_vl, y_vl, criterion)
                fold_metrics.append(eval_res)

                for k, v in eval_res.items():
                    mlflow.log_metric(f"fold_{fold_idx + 1}_{k}", v)

            mean_mae = float(np.mean([m["mae"] for m in fold_metrics]))
            mean_rmse = float(np.mean([m["rmse"] for m in fold_metrics]))
            mean_cov = float(np.mean([m["coverage_80pct"] for m in fold_metrics]))

            mlflow.log_metric("cv_mean_mae", mean_mae)
            mlflow.log_metric("cv_mean_rmse", mean_rmse)
            mlflow.log_metric("cv_mean_coverage_80pct", mean_cov)

            logger.info(
                "pytorch_tft_completed", mean_mae=mean_mae, mean_rmse=mean_rmse, coverage=mean_cov
            )

            return {
                "fold_metrics": fold_metrics,
                "summary": {
                    "mae": mean_mae,
                    "rmse": mean_rmse,
                    "coverage_80pct": mean_cov,
                },
                "device": str(self.device),
            }


tft_trainer = PyTorchTFTTrainer()

if __name__ == "__main__":
    tft_trainer.run_training_pipeline()
