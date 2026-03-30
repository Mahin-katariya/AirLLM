"""Time-window slicing around failure anchors."""

from buscraft.models.reasoning_document import FailureAnchor


def default_window_around_anchor(
    anchor: FailureAnchor,
    *,
    pre_ps: int = 100_000,
    post_ps: int = 100_000,
    default_center: int = 0,
) -> tuple[int, int]:
    center = anchor.sim_time_ps if anchor.sim_time_ps is not None else default_center
    return center - pre_ps, center + post_ps
