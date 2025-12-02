'use client';

import React, { useState, useRef, useEffect } from 'react';
import type { Anchor, Position, Item, ViewMode, ConfigMode } from '@/src/types';

interface StoreMapProps {
  anchors: Anchor[];
  positions: Position[];
  items: Item[];
  setupMode: boolean;
  viewMode?: ViewMode;
  stockHeatmap?: any[];
  restockQueue?: any[];
  highlightedItem?: string | null;
  onAnchorPlace?: (x: number, y: number, anchorIndex: number) => void;
  onAnchorUpdate?: (anchorId: number, x: number, y: number) => void;
  onItemClick?: (item: Item) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function StoreMap({ 
  anchors, 
  positions,
  items,
  setupMode,
  viewMode = 'live',
  stockHeatmap = [],
  restockQueue = [],
  highlightedItem = null,
  onAnchorPlace,
  onAnchorUpdate,
  onItemClick 
}: StoreMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [draggedAnchor, setDraggedAnchor] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [hoveredAnchor, setHoveredAnchor] = useState<number | null>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 640 });
  
  // Dynamic configuration from backend
  const [storeWidth, setStoreWidth] = useState(1000);
  const [storeHeight, setStoreHeight] = useState(800);
  const [currentMode, setCurrentMode] = useState<ConfigMode>('SIMULATION');

  // Fetch store configuration on mount
  useEffect(() => {
    fetch(`${API_URL}/config/store`)
      .then(res => res.json())
      .then(data => {
        setStoreWidth(data.store_width);
        setStoreHeight(data.store_height);
        setCurrentMode(data.mode);
      })
      .catch(err => console.error('Failed to fetch store config:', err));
  }, []);

  // Convert store coordinates (cm) to canvas coordinates (pixels)
  const toCanvasCoords = (x: number, y: number, canvas: HTMLCanvasElement) => {
    const scaleX = canvas.width / storeWidth;
    const scaleY = canvas.height / storeHeight;
    return {
      x: x * scaleX,
      y: y * scaleY
    };
  };

  // Convert canvas coordinates to store coordinates
  const toStoreCoords = (x: number, y: number, canvas: HTMLCanvasElement) => {
    const scaleX = storeWidth / canvas.width;
    const scaleY = storeHeight / canvas.height;
    return {
      x: x * scaleX,
      y: y * scaleY
    };
  };

  // Create smooth gradient heatmap based on item presence/absence
  // Shows individual items: Green = present, Red = missing
  // Creates density effect showing where missing items cluster
  const drawSmoothHeatmap = (ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, heatmapData: any[]) => {
    if (!heatmapData || heatmapData.length === 0) {
      // Show message when no data available
      ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
      ctx.font = 'bold 24px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('No items detected yet', canvas.width / 2, canvas.height / 2 - 20);
      ctx.font = '16px sans-serif';
      ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      ctx.fillText('Run the simulation to detect items', canvas.width / 2, canvas.height / 2 + 15);
      return;
    }
    
    // First, draw a subtle base layer showing all item positions
    // Then overlay with color based on status
    
    // Parameters for heat effect
    const itemRadius = 18;      // Size of each item dot
    const glowRadius = 40;      // Glow/heat effect radius
    
    // Sort so missing items are drawn on top
    const sortedData = [...heatmapData].sort((a, b) => {
      const aDepletion = a.depletion_percentage || 0;
      const bDepletion = b.depletion_percentage || 0;
      return aDepletion - bDepletion; // Draw high depletion (red) on top
    });
    
    // Draw glow/density layer first (creates the "heat" effect)
    sortedData.forEach(location => {
      const pos = toCanvasCoords(location.x, location.y, canvas);
      const depletionPct = (location.depletion_percentage || 0) / 100; // 0 to 1
      const itemsMissing = location.items_missing || 0;
      
      // Create radial gradient for heat effect
      const gradient = ctx.createRadialGradient(
        pos.x, pos.y, 0,
        pos.x, pos.y, glowRadius
      );
      
      if (depletionPct === 0) {
        // Fully stocked - subtle green glow
        gradient.addColorStop(0, 'rgba(34, 197, 94, 0.4)');
        gradient.addColorStop(0.5, 'rgba(34, 197, 94, 0.15)');
        gradient.addColorStop(1, 'rgba(34, 197, 94, 0)');
      } else if (depletionPct < 0.5) {
        // Some missing - yellow/orange glow
        const intensity = 0.3 + depletionPct * 0.4;
        gradient.addColorStop(0, `rgba(251, 191, 36, ${intensity})`);
        gradient.addColorStop(0.5, `rgba(251, 191, 36, ${intensity * 0.4})`);
        gradient.addColorStop(1, 'rgba(251, 191, 36, 0)');
      } else {
        // Many missing - red glow (more intense for worse depletion)
        const intensity = 0.4 + (depletionPct - 0.5) * 0.6;
        gradient.addColorStop(0, `rgba(239, 68, 68, ${intensity})`);
        gradient.addColorStop(0.5, `rgba(239, 68, 68, ${intensity * 0.5})`);
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
      }
      
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, glowRadius, 0, 2 * Math.PI);
      ctx.fill();
    });
    
    // Draw solid item indicators on top
    sortedData.forEach(location => {
      const pos = toCanvasCoords(location.x, location.y, canvas);
      const depletionPct = (location.depletion_percentage || 0) / 100;
      const currentCount = location.current_count || 0;
      const maxItems = location.max_items_seen || 1;
      const itemsMissing = location.items_missing || 0;
      
      // Color based on depletion - smooth gradient
      let r, g, b;
      if (depletionPct === 0) {
        // Perfect - bright green
        r = 34; g = 197; b = 94;
      } else if (depletionPct <= 0.25) {
        // Light depletion - green to yellow-green
        const t = depletionPct / 0.25;
        r = Math.floor(34 + t * (180 - 34));
        g = Math.floor(197 + t * (200 - 197));
        b = Math.floor(94 - t * 70);
      } else if (depletionPct <= 0.5) {
        // Medium depletion - yellow to orange
        const t = (depletionPct - 0.25) / 0.25;
        r = Math.floor(180 + t * (251 - 180));
        g = Math.floor(200 - t * (200 - 146));
        b = Math.floor(24 + t * (36 - 24));
      } else if (depletionPct <= 0.75) {
        // High depletion - orange to red-orange
        const t = (depletionPct - 0.5) / 0.25;
        r = Math.floor(251 - t * (251 - 245));
        g = Math.floor(146 - t * (146 - 90));
        b = Math.floor(36 + t * (50 - 36));
      } else {
        // Critical - red
        const t = (depletionPct - 0.75) / 0.25;
        r = Math.floor(245 - t * (245 - 220));
        g = Math.floor(90 - t * (90 - 38));
        b = Math.floor(50 - t * (50 - 38));
      }
      
      // Draw outer ring (shows severity)
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, itemRadius + 4, 0, 2 * Math.PI);
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.8)`;
      ctx.fill();
      ctx.strokeStyle = `rgb(${Math.max(0, r - 30)}, ${Math.max(0, g - 30)}, ${Math.max(0, b - 30)})`;
      ctx.lineWidth = 2;
      ctx.stroke();
      
      // Draw inner circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, itemRadius, 0, 2 * Math.PI);
      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
      ctx.fill();
      
      // Draw count text
      ctx.fillStyle = depletionPct > 0.5 ? '#ffffff' : '#000000';
      ctx.font = 'bold 12px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      if (itemsMissing > 0) {
        // Show missing count
        ctx.fillText(`-${itemsMissing}`, pos.x, pos.y);
      } else {
        // Show checkmark or count for fully stocked
        ctx.fillText('✓', pos.x, pos.y);
      }
    });
    
    // Draw legend
    drawHeatmapLegend(ctx, canvas);
  };
  
  // Draw heatmap legend
  const drawHeatmapLegend = (ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement) => {
    const legendX = canvas.width - 180;
    const legendY = 20;
    const legendWidth = 160;
    const legendHeight = 100;
    const radius = 8;
    
    // Background with rounded corners (manual implementation for compatibility)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(legendX + radius, legendY);
    ctx.lineTo(legendX + legendWidth - radius, legendY);
    ctx.quadraticCurveTo(legendX + legendWidth, legendY, legendX + legendWidth, legendY + radius);
    ctx.lineTo(legendX + legendWidth, legendY + legendHeight - radius);
    ctx.quadraticCurveTo(legendX + legendWidth, legendY + legendHeight, legendX + legendWidth - radius, legendY + legendHeight);
    ctx.lineTo(legendX + radius, legendY + legendHeight);
    ctx.quadraticCurveTo(legendX, legendY + legendHeight, legendX, legendY + legendHeight - radius);
    ctx.lineTo(legendX, legendY + radius);
    ctx.quadraticCurveTo(legendX, legendY, legendX + radius, legendY);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    
    // Title
    ctx.fillStyle = '#374151';
    ctx.font = 'bold 13px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('Stock Status', legendX + 10, legendY + 10);
    
    // Legend items
    const items = [
      { color: 'rgb(34, 197, 94)', label: 'All Present' },
      { color: 'rgb(251, 191, 36)', label: 'Some Missing' },
      { color: 'rgb(239, 68, 68)', label: 'Many Missing' },
    ];
    
    items.forEach((item, index) => {
      const y = legendY + 35 + index * 22;
      
      // Color dot
      ctx.beginPath();
      ctx.arc(legendX + 20, y, 8, 0, 2 * Math.PI);
      ctx.fillStyle = item.color;
      ctx.fill();
      ctx.strokeStyle = '#00000033';
      ctx.lineWidth = 1;
      ctx.stroke();
      
      // Label
      ctx.fillStyle = '#374151';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(item.label, legendX + 35, y);
    });
  };

  // Draw heatmap overlay for zones (legacy zone-based view)
  const drawHeatmap = (ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, data: any[], type: 'stock' | 'purchase') => {
    if (!data || data.length === 0) return;
    
    if (type === 'stock') {
      // Stock depletion heatmap: green (good) -> yellow (warning) -> red (critical)
      data.forEach(entry => {
        const zone = entry.zone;
        const depletionPct = entry.depletion_percentage || 0;
        const currentCount = entry.current_count || 0;
        const missingCount = entry.missing_count || 0;
        const totalExpected = entry.total_expected || 0;
        
        // Convert zone coordinates
        const topLeft = toCanvasCoords(zone.x_min, zone.y_min, canvas);
        const bottomRight = toCanvasCoords(zone.x_max, zone.y_max, canvas);
        const width = bottomRight.x - topLeft.x;
        const height = bottomRight.y - topLeft.y;
        
        // Color gradient based on depletion percentage:
        // 0% = Green (fully stocked)
        // 50% = Yellow (half depleted)
        // 100% = Red (completely depleted)
        let r, g, b;
        if (depletionPct <= 50) {
          // Green to Yellow: 0-50% depletion
          const ratio = depletionPct / 50;
          r = Math.floor(34 + ratio * (234 - 34));   // 34 -> 234 (green to yellow)
          g = Math.floor(197 - ratio * (197 - 179)); // 197 -> 179
          b = Math.floor(94 - ratio * 94);           // 94 -> 0
        } else {
          // Yellow to Red: 50-100% depletion
          const ratio = (depletionPct - 50) / 50;
          r = Math.floor(234 + ratio * (239 - 234)); // 234 -> 239
          g = Math.floor(179 - ratio * (179 - 68));  // 179 -> 68
          b = 0;
        }
        
        // Darker overlay for higher depletion
        const alpha = 0.4 + (depletionPct / 100) * 0.3;
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
        ctx.fillRect(topLeft.x, topLeft.y, width, height);
        
        // Draw zone border with matching color
        ctx.strokeStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.lineWidth = 3;
        ctx.strokeRect(topLeft.x, topLeft.y, width, height);
        
        // Draw stock information
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 3;
        ctx.font = 'bold 22px sans-serif';
        ctx.textAlign = 'center';
        
        const centerX = topLeft.x + width / 2;
        const centerY = topLeft.y + height / 2;
        
        // Stock status text with outline
        const statusText = `${currentCount}/${totalExpected}`;
        ctx.strokeText(statusText, centerX, centerY - 8);
        ctx.fillText(statusText, centerX, centerY - 8);
        
        // Depletion percentage
        if (depletionPct > 0) {
          ctx.font = 'bold 18px sans-serif';
          const depletionText = `${Math.round(depletionPct)}% depleted`;
          ctx.strokeText(depletionText, centerX, centerY + 18);
          ctx.fillText(depletionText, centerX, centerY + 18);
        } else {
          ctx.font = 'bold 18px sans-serif';
          const fullText = 'Fully Stocked';
          ctx.strokeText(fullText, centerX, centerY + 18);
          ctx.fillText(fullText, centerX, centerY + 18);
        }
      });
    } else {
      // Purchase heatmap: blue (low) -> yellow -> red (high activity)
      const maxValue = Math.max(...data.map(d => d.purchase_count));
      if (maxValue === 0) return;
      
      data.forEach(entry => {
        const zone = entry.zone;
        const value = entry.purchase_count;
        const intensity = value / maxValue;
        
        // Convert zone coordinates
        const topLeft = toCanvasCoords(zone.x_min, zone.y_min, canvas);
        const bottomRight = toCanvasCoords(zone.x_max, zone.y_max, canvas);
        const width = bottomRight.x - topLeft.x;
        const height = bottomRight.y - topLeft.y;
        
        // Heat color: blue (low) -> yellow -> red (high)
        let r, g, b;
        if (intensity < 0.5) {
          r = Math.floor(intensity * 2 * 255);
          g = Math.floor(intensity * 2 * 255);
          b = 255;
        } else {
          r = 255;
          g = Math.floor((1 - intensity) * 2 * 255);
          b = 0;
        }
        
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.4)`;
        ctx.fillRect(topLeft.x, topLeft.y, width, height);
        
        // Draw zone border
        ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.8)`;
        ctx.lineWidth = 3;
        ctx.strokeRect(topLeft.x, topLeft.y, width, height);
        
        // Draw value label with outline for readability
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 3;
        ctx.font = 'bold 24px sans-serif';
        ctx.textAlign = 'center';
        const centerX = topLeft.x + width / 2;
        const centerY = topLeft.y + height / 2;
        ctx.strokeText(value.toString(), centerX, centerY);
        ctx.fillText(value.toString(), centerX, centerY);
      });
    }
  };

  // Draw the entire map
  const drawMap = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas with white background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid - scale grid size based on store dimensions for nice divisions
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    
    // Calculate appropriate grid size (aim for 5-10 divisions per axis)
    const getGridSize = (dimension: number) => {
      if (dimension <= 200) return 20;
      if (dimension <= 500) return 50;
      if (dimension <= 1000) return 100;
      if (dimension <= 2000) return 200;
      return 500;
    };
    
    const gridSizeX = getGridSize(storeWidth);
    const gridSizeY = getGridSize(storeHeight);
    
    // Draw vertical grid lines
    for (let x = 0; x <= storeWidth; x += gridSizeX) {
      const canvasX = toCanvasCoords(x, 0, canvas).x;
      ctx.beginPath();
      ctx.moveTo(canvasX, 0);
      ctx.lineTo(canvasX, canvas.height);
      ctx.stroke();
      
      // Draw coordinate label at top
      if (setupMode && x > 0 && x < storeWidth) {
        ctx.fillStyle = '#9ca3af';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`${x}`, canvasX, 14);
      }
    }
    
    // Draw horizontal grid lines
    for (let y = 0; y <= storeHeight; y += gridSizeY) {
      const canvasY = toCanvasCoords(0, y, canvas).y;
      ctx.beginPath();
      ctx.moveTo(0, canvasY);
      ctx.lineTo(canvas.width, canvasY);
      ctx.stroke();
      
      // Draw coordinate label at left
      if (setupMode && y > 0 && y < storeHeight) {
        ctx.fillStyle = '#9ca3af';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(`${y}`, 4, canvasY + 4);
      }
    }

    // Draw store boundary
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 4;
    ctx.strokeRect(0, 0, canvas.width, canvas.height);

    // Draw aisles only in SIMULATION mode
    if (currentMode === 'SIMULATION') {
      // Draw aisles (4 vertical aisles at x=200, 400, 600, 800)
      const aisleX = [200, 400, 600, 800];
      const aisleStartY = 150;
      const aisleEndY = 700;
      const aisleWidth = 80; // 80cm wide aisles
      
      aisleX.forEach((x, index) => {
        const leftEdge = toCanvasCoords(x - aisleWidth / 2, aisleStartY, canvas);
        const rightEdge = toCanvasCoords(x + aisleWidth / 2, aisleStartY, canvas);
        const bottomY = toCanvasCoords(x, aisleEndY, canvas).y;
        
        // Draw aisle background
        ctx.fillStyle = 'rgba(243, 244, 246, 0.8)';
        ctx.fillRect(leftEdge.x, leftEdge.y, rightEdge.x - leftEdge.x, bottomY - leftEdge.y);
        
        // Draw aisle borders (shelving edges)
        ctx.strokeStyle = '#9ca3af';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(leftEdge.x, leftEdge.y);
        ctx.lineTo(leftEdge.x, bottomY);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(rightEdge.x, leftEdge.y);
        ctx.lineTo(rightEdge.x, bottomY);
        ctx.stroke();
        
        // Draw aisle label
        ctx.fillStyle = '#6b7280';
        ctx.font = 'bold 28px sans-serif';
        ctx.textAlign = 'center';
        const labelPos = toCanvasCoords(x, aisleStartY - 30, canvas);
        ctx.fillText(`Aisle ${index + 1}`, labelPos.x, labelPos.y);
      });
      
      // Draw cross aisle (horizontal at y=400)
      const crossAisleY = 400;
      const crossAisleHeight = 80;
      const crossLeftEdge = toCanvasCoords(0, crossAisleY - crossAisleHeight / 2, canvas);
      const crossRightEdge = toCanvasCoords(storeWidth, crossAisleY + crossAisleHeight / 2, canvas);
      
      ctx.fillStyle = 'rgba(243, 244, 246, 0.6)';
      ctx.fillRect(0, crossLeftEdge.y, canvas.width, crossRightEdge.y - crossLeftEdge.y);
      ctx.strokeStyle = '#d1d5db';
      ctx.lineWidth = 2;
      ctx.strokeRect(0, crossLeftEdge.y, canvas.width, crossRightEdge.y - crossLeftEdge.y);
    }

    // Draw heatmap overlays for non-live modes
    if (viewMode === 'stock-heatmap') {
      // Use smooth gradient heatmap based on depletion percentage
      console.log('Drawing heatmap with data:', stockHeatmap);
      drawSmoothHeatmap(ctx, canvas, stockHeatmap);
    }

    // Draw items on the map (only in live mode)
    if (viewMode === 'live') {
      const missingItems = items.filter(item => item.status === 'not present');
      const presentItems = items.filter(item => item.status !== 'not present');
      
      // Draw present items first (so missing items are on top)
      presentItems.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      const isHighlighted = highlightedItem && item.product_id === highlightedItem;
      
      // Draw highlight glow if this item is selected
      if (isHighlighted) {
        ctx.fillStyle = 'rgba(255, 215, 0, 0.4)';  // Gold glow
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 28, 0, 2 * Math.PI);
        ctx.fill();
      }
      
      // Draw item as small square with subtle glow
      ctx.fillStyle = isHighlighted ? 'rgba(255, 215, 0, 0.9)' : 'rgba(34, 197, 94, 0.6)';  // Gold if highlighted, green otherwise
      ctx.fillRect(pos.x - 6, pos.y - 6, 12, 12);
      ctx.strokeStyle = isHighlighted ? '#FFD700' : '#22c55e';
      ctx.lineWidth = isHighlighted ? 4 : 2;
      ctx.strokeRect(pos.x - 6, pos.y - 6, 12, 12);
    });
    
    // Draw missing items on top with emphasis
    missingItems.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      const isHighlighted = highlightedItem && item.product_id === highlightedItem;
      
      // Pulsing glow effect for missing items
      ctx.fillStyle = isHighlighted ? 'rgba(255, 215, 0, 0.4)' : 'rgba(239, 68, 68, 0.3)';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, isHighlighted ? 32 : 24, 0, 2 * Math.PI);
      ctx.fill();
      
      // Draw missing item as prominent square
      ctx.fillStyle = isHighlighted ? '#FFD700' : '#ef4444';  // Gold if highlighted, red otherwise
      ctx.fillRect(pos.x - 10, pos.y - 10, 20, 20);
      ctx.strokeStyle = isHighlighted ? '#FFA500' : '#fca5a5';
      ctx.lineWidth = isHighlighted ? 6 : 4;
      ctx.strokeRect(pos.x - 10, pos.y - 10, 20, 20);
      
      // Draw warning icon
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 32px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('!', pos.x, pos.y + 10);
    });
    }

    // Draw distance circles from anchors to tags (only for the most recent position in live mode)
    if (viewMode === 'live' && !setupMode && positions.length > 0) {
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.15)';
      ctx.lineWidth = 2;
      
      // Only draw circles for the first (most recent) position
      const recentPos = positions[0];
      anchors.forEach(anchor => {
        if (!anchor.is_active) return;
        
        const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
        const distance = Math.sqrt(
          Math.pow(recentPos.x_position - anchor.x_position, 2) +
          Math.pow(recentPos.y_position - anchor.y_position, 2)
        );
        
        const radiusPx = distance * (canvas.width / storeWidth);
        
        ctx.beginPath();
        ctx.arc(anchorCanvas.x, anchorCanvas.y, radiusPx, 0, 2 * Math.PI);
        ctx.stroke();
      });
    }

    // Draw anchors
    anchors.forEach((anchor, index) => {
      const pos = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      const isHovered = hoveredAnchor === anchor.id || draggedAnchor === anchor.id;
      
      // Draw outer ring for better visibility
      ctx.strokeStyle = anchor.is_active ? 'rgba(0, 85, 164, 0.3)' : 'rgba(156, 163, 175, 0.3)';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 32, 0, 2 * Math.PI);
      ctx.stroke();
      
      // Anchor circle - royal blue
      ctx.fillStyle = anchor.is_active ? '#0055A4' : '#9ca3af';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 24, 0, 2 * Math.PI);
      ctx.fill();
      
      // White border
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 24, 0, 2 * Math.PI);
      ctx.stroke();
      
      // Highlight if hovered or dragged
      if (isHovered) {
        ctx.strokeStyle = '#fbbf24';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 36, 0, 2 * Math.PI);
        ctx.stroke();
      }
      
      // Anchor number inside circle
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 20px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${index + 1}`, pos.x, pos.y);
      ctx.textBaseline = 'alphabetic';
      
      // Anchor name label (above)
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 18px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(anchor.name || `Anchor ${index + 1}`, pos.x, pos.y - 44);
      
      // MAC address (below)
      ctx.font = '14px monospace';
      ctx.fillStyle = '#6b7280';
      ctx.fillText(anchor.mac_address, pos.x, pos.y + 44);
      
      // Position coordinates in setup mode
      if (setupMode) {
        ctx.font = '12px sans-serif';
        ctx.fillStyle = '#9ca3af';
        ctx.fillText(`(${Math.round(anchor.x_position)}, ${Math.round(anchor.y_position)})`, pos.x, pos.y + 58);
      }
    });

    // Draw employee positions (from UWB triangulation) - only in live mode
    if (viewMode === 'live' && positions.length > 0) {
      // Draw current employee position (most recent)
      const currentPos = positions[0];
      const canvasPos = toCanvasCoords(currentPos.x_position, currentPos.y_position, canvas);
      
      // 1.5m detection radius circle (RFID range)
      ctx.strokeStyle = 'rgba(0, 85, 164, 0.3)';
      ctx.lineWidth = 4;
      ctx.setLineDash([16, 8]);
      const radiusCm = 150; // 1.5 meters RFID range
      const radiusPx = radiusCm * (canvas.width / storeWidth);
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, radiusPx, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Outer glow for employee
      ctx.fillStyle = 'rgba(0, 85, 164, 0.15)';
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, 48, 0, 2 * Math.PI);
      ctx.fill();
      
      // Employee icon - royal blue (scaled 2x)
      ctx.fillStyle = '#0055A4';
      ctx.strokeStyle = '#1a6bbb';
      ctx.lineWidth = 4;
      
      // Head
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y - 16, 16, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
      
      // Body
      ctx.fillStyle = '#0055A4';
      ctx.fillRect(canvasPos.x - 12, canvasPos.y + 4, 24, 28);
      ctx.strokeRect(canvasPos.x - 12, canvasPos.y + 4, 24, 28);
      
      // Employee label
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 26px sans-serif';
      ctx.textAlign = 'center';
      ctx.shadowColor = 'rgba(255, 255, 255, 0.9)';
      ctx.shadowBlur = 6;
      ctx.fillText('Employee', canvasPos.x, canvasPos.y - 64);
      ctx.shadowBlur = 0;
      
      // Position coordinates
      ctx.font = '20px monospace';
      ctx.fillStyle = '#374151';
      ctx.fillText(`(${Math.round(currentPos.x_position)}, ${Math.round(currentPos.y_position)})`, canvasPos.x, canvasPos.y + 60);
    }

  };

  // Removed drawMissingItemsAlert function - now displayed in sidebar

  // Handle responsive canvas sizing
  useEffect(() => {
    const updateCanvasSize = () => {
      if (!containerRef.current) return;
      
      const container = containerRef.current;
      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;
      
      // Maintain aspect ratio based on store dimensions
      const aspectRatio = storeWidth / storeHeight;
      
      let width = containerWidth;
      let height = width / aspectRatio;
      
      // If height exceeds container, constrain by height instead
      if (height > containerHeight) {
        height = containerHeight;
        width = height * aspectRatio;
      }
      
      // Increase resolution by 2x for sharper rendering
      setCanvasSize({ 
        width: Math.floor(width * 2), 
        height: Math.floor(height * 2) 
      });
    };
    
    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);
    
    return () => window.removeEventListener('resize', updateCanvasSize);
  }, [storeWidth, storeHeight]);

  // Redraw when data changes
  useEffect(() => {
    drawMap();
    // Removed drawMissingItemsAlert - now shown in sidebar instead
  }, [anchors, positions, items, setupMode, hoveredAnchor, draggedAnchor, canvasSize, viewMode, stockHeatmap, storeWidth, storeHeight, currentMode]);

  // Removed auto-pulsing animation for missing items alert (now shown in sidebar)

  // Handle canvas click (place new anchor in setup mode)
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    // Get click position in displayed coordinates
    const displayX = e.clientX - rect.left;
    const displayY = e.clientY - rect.top;
    
    // Scale up to actual canvas resolution (canvas is 2x for high DPI)
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = displayX * scaleX;
    const y = displayY * scaleY;
    
    // If in setup mode, handle anchor placement
    if (setupMode && onAnchorPlace) {
      // Don't place if we were dragging an existing anchor
      if (isDragging || draggedAnchor !== null) {
        return;
      }
      
      // Check if clicking on an existing anchor (don't create new one)
      for (const anchor of anchors) {
        const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
        const distance = Math.sqrt(
          Math.pow(x - anchorCanvas.x, 2) + Math.pow(y - anchorCanvas.y, 2)
        );
        if (distance < 40) {
          return; // Clicked on existing anchor, don't create new
        }
      }
      
      const storeCoords = toStoreCoords(x, y, canvas);
      // Use anchors.length as index - page.tsx will handle the actual creation
      onAnchorPlace(storeCoords.x, storeCoords.y, anchors.length);
      return;
    }
    
    // If in live mode and onItemClick is provided, check for item clicks
    if (viewMode === 'live' && onItemClick) {
      const storeCoords = toStoreCoords(x, y, canvas);
      const clickRadius = 15; // pixels
      
      // Check if click is near any item
      for (const item of items) {
        const distance = Math.sqrt(
          Math.pow(storeCoords.x - item.x_position, 2) + 
          Math.pow(storeCoords.y - item.y_position, 2)
        );
        
        // Convert distance to canvas pixels for comparison
        const distancePx = distance * (canvas.width / storeWidth);
        
        if (distancePx < clickRadius) {
          onItemClick(item);
          return;
        }
      }
    }
  };

  // Handle mouse down (start dragging)
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!setupMode) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const displayX = e.clientX - rect.left;
    const displayY = e.clientY - rect.top;
    
    // Scale up to actual canvas resolution (canvas is 2x for high DPI)
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = displayX * scaleX;
    const y = displayY * scaleY;
    
    // Check if clicking on an anchor to start dragging
    for (const anchor of anchors) {
      const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      const distance = Math.sqrt(
        Math.pow(x - anchorCanvas.x, 2) + Math.pow(y - anchorCanvas.y, 2)
      );
      
      if (distance < 40) {  // Increased radius for easier clicking
        setDraggedAnchor(anchor.id);
        setIsDragging(false); // Will be set to true on first move
        e.preventDefault(); // Prevent click event
        break;
      }
    }
  };

  // Handle mouse move (dragging)
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const displayX = e.clientX - rect.left;
    const displayY = e.clientY - rect.top;
    
    // Scale up to actual canvas resolution (canvas is 2x for high DPI)
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = displayX * scaleX;
    const y = displayY * scaleY;
    
    if (draggedAnchor !== null && setupMode && onAnchorUpdate) {
      setIsDragging(true); // Mark that we're actually dragging
      const storeCoords = toStoreCoords(x, y, canvas);
      onAnchorUpdate(draggedAnchor, storeCoords.x, storeCoords.y);
    }
    
    // Update hover state
    let hovering = null;
    for (const anchor of anchors) {
      const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      const distance = Math.sqrt(
        Math.pow(x - anchorCanvas.x, 2) + Math.pow(y - anchorCanvas.y, 2)
      );
      
      if (distance < 30) {  // Increased radius for easier hovering
        hovering = anchor.id;
        break;
      }
    }
    setHoveredAnchor(hovering);
  };

  // Handle mouse up (stop dragging)
  const handleMouseUp = () => {
    // Small delay to prevent click event from firing after drag
    setTimeout(() => {
      setDraggedAnchor(null);
      setIsDragging(false);
    }, 10);
  };

  return (
    <div ref={containerRef} className="relative w-full h-full flex items-center justify-center">
      <canvas
        ref={canvasRef}
        width={canvasSize.width}
        height={canvasSize.height}
        style={{
          width: `${canvasSize.width / 2}px`,
          height: `${canvasSize.height / 2}px`
        }}
        className="border-2 border-gray-300 cursor-crosshair"
        onClick={handleCanvasClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
      
      {setupMode && (
        <div className="absolute top-4 right-4 bg-[#0055A4] text-white px-4 py-2 text-sm font-medium rounded-lg shadow-lg">
          <div className="font-semibold">Setup Mode</div>
          <div className="text-blue-100 text-xs mt-1">
            Click to place Anchor #{anchors.length + 1}<br/>
            Drag anchors to reposition
          </div>
        </div>
      )}

    </div>
  );
}
