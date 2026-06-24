from pathlib import Path

import matplotlib.pyplot as plt


def get_plot_data():
    categories = ["CĂ³ thá»ƒ tráº£ lá»i", "KhĂ´ng thá»ƒ tráº£ lá»i"]
    series = [
        ("GPT-4o-mini Few-shot", [96.21, 48.53], "#9ecae1"),
        ("GPT-4o-mini POMA", [95.84, 51.28], "#3182bd"),
        ("Qwen3-8B Few-shot", [97.38, 56.64], "#a1d99b"),
        ("Qwen3-8B POMA", [96.49, 51.13], "#31a354"),
    ]
    return categories, series


def build_figure():
    categories, series = get_plot_data()
    group_centers = [0.0, 1.8]
    width = 0.24

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)

    for index, (label, values, color) in enumerate(series):
        offset = (index - (len(series) - 1) / 2) * width
        bars = ax.bar(
            [center + offset for center in group_centers],
            values,
            width,
            label=label,
            color=color,
        )
        ax.bar_label(bars, fmt="%.2f", padding=3, rotation=90, fontsize=8)

    ax.set_ylabel("F1-score")
    ax.set_ylim(0, 112)
    ax.set_xticks(group_centers, categories)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(
        ncol=2,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        fontsize=8,
    )

    fig.tight_layout()
    return fig, ax


def main() -> None:
    output_path = (
        Path(__file__).resolve().parents[1]
        / "paper"
        / "latex"
        / "imgs"
        / "answerability_f1.png"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, _ = build_figure()
    fig.savefig(output_path, dpi=1000, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
