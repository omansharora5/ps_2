"""Optional compact image research heads; importing this module does not import Torch."""

import numpy as np

from .regional_science import validate_survival


def make_regional_model(channels, *, hidden=12, bins=6):
    if not all(type(x) is int and x > 0 for x in (channels, hidden, bins)) or bins > 24 or hidden > 128 or channels > 64:
        raise ValueError("Model dimensions exceed the bounded research contract")
    import torch
    from torch import nn

    class RegionalConvLSTM(nn.Module):
        def __init__(self):
            super().__init__()
            self.gates = nn.Conv2d(channels + hidden, hidden * 4, 3, padding=1)
            self.lightning = nn.Conv2d(hidden, 1, 1)
            self.rain_onset = nn.Conv2d(hidden, bins, 1)
            self.lightning_onset = nn.Conv2d(hidden, bins, 1)

        def forward(self, sequence):
            if sequence.ndim != 5 or sequence.shape[2] != channels or sequence.shape[1] < 1:
                raise ValueError("Expected [batch,history,channels,height,width] image sequences")
            batch, _, _, height, width = sequence.shape
            state = sequence.new_zeros((batch, hidden, height, width))
            cell = torch.zeros_like(state)
            for frame in sequence.unbind(1):
                i, f, o, candidate = self.gates(torch.cat([frame, state], dim=1)).chunk(4, dim=1)
                cell = torch.sigmoid(f) * cell + torch.sigmoid(i) * torch.tanh(candidate)
                state = torch.sigmoid(o) * torch.tanh(cell)
            return {"lightning_logits": self.lightning(state).squeeze(1),
                    "rain_onset_logits": self.rain_onset(state).movedim(1, -1),
                    "lightning_onset_logits": self.lightning_onset(state).movedim(1, -1)}

    return RegionalConvLSTM()


def _survival_loss(logits, target):
    import torch
    import torch.nn.functional as functional
    _, event, observed, mask = validate_survival(logits.detach().cpu().numpy(), *target)
    count = int(mask.sum())
    if not count:
        return torch.where(torch.isfinite(logits), logits, 0).sum() * 0, count
    mask_t = torch.as_tensor(mask, device=logits.device)
    z = logits[mask_t]
    event = torch.as_tensor(event[mask], device=z.device)
    observed = torch.as_tensor(observed[mask], device=z.device)
    steps = torch.arange(z.shape[-1], device=z.device)
    survived = steps < torch.where(event >= 0, event, observed).unsqueeze(-1)
    struck = (event.unsqueeze(-1) == steps) & (event.unsqueeze(-1) >= 0)
    return (functional.softplus(z) * survived + functional.softplus(-z) * struck).sum(-1).mean(), count


def regional_loss(outputs, *, lightning_targets, lightning_coverage, rain_onset, lightning_onset):
    """Equal task weights; onset tuples are (event_bin, observed_bins, coverage)."""
    import torch
    import torch.nn.functional as functional
    z = outputs["lightning_logits"]
    y, mask = np.asarray(lightning_targets), np.asarray(lightning_coverage)
    if y.shape != tuple(z.shape) or mask.shape != y.shape or not np.isin(mask, [0, 1]).all():
        raise ValueError("Lightning target/coverage dimensions must match event logits")
    mask = mask.astype(bool)
    if not np.isin(y[mask], [0, 1]).all() or not torch.isfinite(z[torch.as_tensor(mask, device=z.device)]).all():
        raise ValueError("Covered lightning labels must be binary and logits finite")
    count = int(mask.sum())
    event_loss = functional.binary_cross_entropy_with_logits(z[torch.as_tensor(mask, device=z.device)],
        torch.as_tensor(y[mask], dtype=z.dtype, device=z.device)) if count else torch.where(torch.isfinite(z), z, 0).sum() * 0
    rain_loss, rain_count = _survival_loss(outputs["rain_onset_logits"], rain_onset)
    lightning_loss, lightning_count = _survival_loss(outputs["lightning_onset_logits"], lightning_onset)
    active = sum(n > 0 for n in (count, rain_count, lightning_count))
    if not active:
        raise ValueError("No covered labels in any regional task")
    return {"loss": (event_loss + rain_loss + lightning_loss) / active,
            "lightning_bce": event_loss, "rain_onset_nll": rain_loss, "lightning_onset_nll": lightning_loss,
            "covered_counts": {"lightning": count, "rain_onset": rain_count, "lightning_onset": lightning_count}}
