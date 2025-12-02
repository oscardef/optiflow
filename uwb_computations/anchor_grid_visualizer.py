"""
Anchor Grid Visualizer

Hexagonal grid placement algorithm.
Click inside the rectangle to see coverage.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import Slider
import numpy as np

# Parameters
AREA = 4850  # m²
ASPECT_RATIO = 1.5  # WIDTH / HEIGHT (e.g., 1.5 means width is 1.5x height)
HEIGHT = np.sqrt(AREA / ASPECT_RATIO)
WIDTH = HEIGHT * ASPECT_RATIO
RADIUS = 10  # meters


def create_hexagonal_grid(spacing, x_min, x_max, y_min, y_max):
    """Create hexagonal grid of anchors starting from top-left corner."""
    vertical_spacing = spacing * np.sqrt(3) / 2
    anchors = []
    
    # Start at the walls (x=0, y=side_length is top-left)
    row = 0
    y = y_max  # Start from top
    while y >= y_min:  # Go down to bottom
        x_offset = (spacing / 2) if (row % 2 == 1) else 0
        x = x_min + x_offset  # Start from left wall
        while x <= x_max:
            anchors.append((x, y))
            x += spacing
        y -= vertical_spacing
        row += 1
    
    return anchors





def hex_coverage_at_worst_point(spacing, radius):
    """
    In an infinite hexagonal grid, compute minimum coverage at the worst point.
    """
    d = spacing
    h = d * np.sqrt(3) / 2
    
    test_points = []
    for px in np.linspace(0, d, 15):
        for py in np.linspace(0, h, 15):
            test_points.append((px, py))
    
    min_count = float('inf')
    
    for (test_x, test_y) in test_points:
        count = 0
        for row in range(-15, 16):
            y_anchor = row * h
            x_offset = (d / 2) if (row % 2 != 0) else 0
            for col in range(-15, 16):
                x_anchor = col * d + x_offset
                dist = np.sqrt((x_anchor - test_x)**2 + (y_anchor - test_y)**2)
                if dist <= radius + 0.001:
                    count += 1
        min_count = min(min_count, count)
    
    return min_count


def find_optimal_spacing_for_n(n_required, radius):
    """
    Find the LARGEST spacing that guarantees at least N anchors coverage
    at the worst point in an infinite hexagonal grid.
    """
    best_spacing = 0.5
    
    for test_spacing in np.arange(0.5, radius * 2.5, 0.5):
        coverage = hex_coverage_at_worst_point(test_spacing, radius)
        if coverage >= n_required:
            best_spacing = test_spacing
        else:
            break
    
    # Binary search for precision
    spacing_low = max(0.5, best_spacing - 1.0)
    spacing_high = best_spacing + 1.0
    
    for _ in range(30):
        spacing = (spacing_low + spacing_high) / 2
        coverage = hex_coverage_at_worst_point(spacing, radius)
        
        if coverage >= n_required:
            spacing_low = spacing
            best_spacing = spacing
        else:
            spacing_high = spacing
        
        if spacing_high - spacing_low < 0.01:
            break
    
    return best_spacing


def compute_grid(n_required, width, height, radius):
    """
    Compute anchor grid using hexagonal placement.
    """
    # Find optimal spacing for coverage
    spacing = find_optimal_spacing_for_n(n_required, radius)
    
    # Create hexagonal grid
    anchors = create_hexagonal_grid(spacing, 0, width, 0, height)
    n_anchors = len(anchors)
    
    # Calculate minimum coverage
    ax_arr = np.array([a[0] for a in anchors])
    ay_arr = np.array([a[1] for a in anchors])
    
    min_cov = float('inf')
    for x in np.linspace(0, width, 50):
        for y in np.linspace(0, height, 50):
            dist = np.sqrt((ax_arr - x)**2 + (ay_arr - y)**2)
            count = np.sum(dist <= radius)
            min_cov = min(min_cov, count)
    
    # Convert to arrays
    ax = np.array([a[0] for a in anchors])
    ay = np.array([a[1] for a in anchors])
    
    return ax, ay, spacing, min_cov, n_anchors


# ============ VISUALIZATION ============

initial_n = 3
anchor_x, anchor_y, spacing, min_cov, n_anchors = compute_grid(
    initial_n, WIDTH, HEIGHT, RADIUS
)

fig, ax = plt.subplots(figsize=(12, 9))
plt.subplots_adjust(bottom=0.12)

ax.set_xlim(-3, WIDTH + 3)
ax.set_ylim(-3, HEIGHT + 3)
ax.set_aspect('equal')
ax.set_xlabel('X (meters)')
ax.set_ylabel('Y (meters)')

# Draw boundary
boundary = patches.Rectangle((0, 0), WIDTH, HEIGHT, 
                               linewidth=2, edgecolor='black', 
                               facecolor='lightgray', alpha=0.2)
ax.add_patch(boundary)

# Plot anchors
scatter_anchors = ax.scatter(anchor_x, anchor_y, 
                              c='blue', s=50, zorder=5, label='Anchors', marker='o')

ax.grid(True, alpha=0.2)
ax.legend(loc='upper right')

# Slider
ax_slider = plt.axes([0.2, 0.04, 0.6, 0.03])
slider_n = Slider(ax_slider, 'Min Anchors (N)', 1, 10, valinit=initial_n, valstep=1)

# Title
title = ax.set_title(
    f'{n_anchors} anchors | Spacing: {spacing:.1f}m | Min coverage: {min_cov}'
)

# Click visualization
circle = None
count_text = None
highlight = None


def update(val=None):
    global anchor_x, anchor_y, spacing, min_cov, n_anchors
    global scatter_anchors
    global circle, count_text, highlight
    
    n_req = int(slider_n.val)
    anchor_x, anchor_y, spacing, min_cov, n_anchors = compute_grid(
        n_req, WIDTH, HEIGHT, RADIUS
    )
    
    scatter_anchors.remove()
    scatter_anchors = ax.scatter(anchor_x, anchor_y, 
                                  c='blue', s=50, zorder=5, marker='o')
    
    # Clear click visuals
    if circle: circle.remove(); circle = None
    if count_text: count_text.remove(); count_text = None
    if highlight: highlight.remove(); highlight = None
    
    title.set_text(
        f'{n_anchors} anchors | Spacing: {spacing:.1f}m | Min coverage: {min_cov}'
    )
    
    fig.canvas.draw_idle()
    print(f"N={n_req}: {n_anchors} anchors, spacing={spacing:.2f}m, min_coverage={min_cov}")


slider_n.on_changed(update)


def on_click(event):
    global circle, count_text, highlight
    
    if event.inaxes != ax:
        return
    
    cx, cy = event.xdata, event.ydata
    
    # Only allow clicks inside the rectangle
    if not (0 <= cx <= WIDTH and 0 <= cy <= HEIGHT):
        return
    
    # Clear old
    if circle: circle.remove()
    if count_text: count_text.remove()
    if highlight: highlight.remove()
    
    # Draw circle
    circle = patches.Circle((cx, cy), RADIUS, linewidth=2, edgecolor='red', 
                             facecolor='red', alpha=0.15, zorder=3)
    ax.add_patch(circle)
    
    # Count anchors
    dist = np.sqrt((anchor_x - cx)**2 + (anchor_y - cy)**2)
    in_range = dist <= RADIUS
    count = np.sum(in_range)
    
    # Highlight
    highlight = ax.scatter(anchor_x[in_range], anchor_y[in_range], 
                           c='lime', s=100, zorder=6, edgecolors='darkgreen', linewidths=2)
    
    # Label
    n_req = int(slider_n.val)
    color = 'lightgreen' if count >= n_req else 'salmon'
    status = '✓' if count >= n_req else '✗'
    
    count_text = ax.text(cx, cy + RADIUS + 1.5, f'{status} {count} anchors', 
                         fontsize=11, fontweight='bold', ha='center',
                         bbox=dict(boxstyle='round', facecolor=color, alpha=0.9), zorder=7)
    
    fig.canvas.draw()


fig.canvas.mpl_connect('button_press_event', on_click)

plt.show()
