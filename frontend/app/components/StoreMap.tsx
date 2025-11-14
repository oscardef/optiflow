'use client';

import React, { useState, useRef, useEffect } from 'react';

interface Anchor {
  id: number;
  mac_address: string;
  name: string;
  x_position: number;
  y_position: number;
  is_active: boolean;
}

interface Position {
  id: number;
  tag_id: string;
  x_position: number;
  y_position: number;
  confidence: number;
  timestamp: string;
}

interface Item {
  product_id: string;
  product_name: string;
  x_position: number;
  y_position: number;
  status: string; // "present", "missing", "unknown"
}

interface StoreMapProps {
  anchors: Anchor[];
  positions: Position[];
  items: Item[];
  setupMode: boolean;
  onAnchorPlace?: (x: number, y: number, anchorIndex: number) => void;
  onAnchorUpdate?: (anchorId: number, x: number, y: number) => void;
}

const STORE_WIDTH = 1000;  // 10 meters in cm
const STORE_HEIGHT = 800;  // 8 meters in cm

export default function StoreMap({ 
  anchors, 
  positions,
  items,
  setupMode, 
  onAnchorPlace,
  onAnchorUpdate 
}: StoreMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [draggedAnchor, setDraggedAnchor] = useState<number | null>(null);
  const [hoveredAnchor, setHoveredAnchor] = useState<number | null>(null);
  const [nextAnchorIndex, setNextAnchorIndex] = useState(0);
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 640 });
  const [legendCollapsed, setLegendCollapsed] = useState(false);

  // Convert store coordinates (cm) to canvas coordinates (pixels)
  const toCanvasCoords = (x: number, y: number, canvas: HTMLCanvasElement) => {
    const scaleX = canvas.width / STORE_WIDTH;
    const scaleY = canvas.height / STORE_HEIGHT;
    return {
      x: x * scaleX,
      y: y * scaleY
    };
  };

  // Convert canvas coordinates to store coordinates
  const toStoreCoords = (x: number, y: number, canvas: HTMLCanvasElement) => {
    const scaleX = STORE_WIDTH / canvas.width;
    const scaleY = STORE_HEIGHT / canvas.height;
    return {
      x: x * scaleX,
      y: y * scaleY
    };
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

    // Draw grid
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 2;
    const gridSize = 100; // 1 meter grid
    for (let x = 0; x < STORE_WIDTH; x += gridSize) {
      const canvasX = toCanvasCoords(x, 0, canvas).x;
      ctx.beginPath();
      ctx.moveTo(canvasX, 0);
      ctx.lineTo(canvasX, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < STORE_HEIGHT; y += gridSize) {
      const canvasY = toCanvasCoords(0, y, canvas).y;
      ctx.beginPath();
      ctx.moveTo(0, canvasY);
      ctx.lineTo(canvas.width, canvasY);
      ctx.stroke();
    }

    // Draw store boundary
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 4;
    ctx.strokeRect(0, 0, canvas.width, canvas.height);

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
    const crossRightEdge = toCanvasCoords(STORE_WIDTH, crossAisleY + crossAisleHeight / 2, canvas);
    
    ctx.fillStyle = 'rgba(243, 244, 246, 0.6)';
    ctx.fillRect(0, crossLeftEdge.y, canvas.width, crossRightEdge.y - crossLeftEdge.y);
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, crossLeftEdge.y, canvas.width, crossRightEdge.y - crossLeftEdge.y);

    // Draw items on the map
    const missingItems = items.filter(item => item.status === 'missing');
    const presentItems = items.filter(item => item.status !== 'missing');
    
    // Draw present items first (so missing items are on top)
    presentItems.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      
      // Draw item as small square with subtle glow
      ctx.fillStyle = 'rgba(34, 197, 94, 0.6)';  // Green for present
      ctx.fillRect(pos.x - 6, pos.y - 6, 12, 12);
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 2;
      ctx.strokeRect(pos.x - 6, pos.y - 6, 12, 12);
    });
    
    // Draw missing items on top with emphasis
    missingItems.forEach((item) => {
      const pos = toCanvasCoords(item.x_position, item.y_position, canvas);
      
      // Pulsing glow effect for missing items
      ctx.fillStyle = 'rgba(239, 68, 68, 0.3)';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 24, 0, 2 * Math.PI);
      ctx.fill();
      
      // Draw missing item as prominent square
      ctx.fillStyle = '#ef4444';  // Bright red
      ctx.fillRect(pos.x - 10, pos.y - 10, 20, 20);
      ctx.strokeStyle = '#fca5a5';
      ctx.lineWidth = 4;
      ctx.strokeRect(pos.x - 10, pos.y - 10, 20, 20);
      
      // Draw warning icon
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 32px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('!', pos.x, pos.y + 10);
    });

    // Draw distance circles from anchors to tags (only for the most recent position)
    if (!setupMode && positions.length > 0) {
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
        
        const radiusPx = distance * (canvas.width / STORE_WIDTH);
        
        ctx.beginPath();
        ctx.arc(anchorCanvas.x, anchorCanvas.y, radiusPx, 0, 2 * Math.PI);
        ctx.stroke();
      });
    }

    // Draw anchors
    anchors.forEach((anchor, index) => {
      const pos = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      
      // Anchor circle - royal blue
      ctx.fillStyle = anchor.is_active ? '#0055A4' : '#9ca3af';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 24, 0, 2 * Math.PI);
      ctx.fill();
      
      // Highlight if hovered or dragged
      if (hoveredAnchor === anchor.id || draggedAnchor === anchor.id) {
        ctx.strokeStyle = '#1a6bbb';
        ctx.lineWidth = 6;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 30, 0, 2 * Math.PI);
        ctx.stroke();
      }
      
      // Anchor label
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 24px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(anchor.name || anchor.mac_address, pos.x, pos.y - 40);
      
      // MAC address
      ctx.font = '20px sans-serif';
      ctx.fillStyle = '#6b7280';
      ctx.fillText(anchor.mac_address, pos.x, pos.y + 60);
    });

    // Draw employee positions (from UWB triangulation)
    if (positions.length > 0) {
      // Draw trail for previous positions (fading)
      for (let i = Math.min(positions.length - 1, 5); i > 0; i--) {
        const pos = positions[i];
        const canvasPos = toCanvasCoords(pos.x_position, pos.y_position, canvas);
        const alpha = (5 - i) / 8;
        
        ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
        ctx.beginPath();
        ctx.arc(canvasPos.x, canvasPos.y, 8, 0, 2 * Math.PI);
        ctx.fill();
      }
      
      // Draw current employee position (most recent)
      const currentPos = positions[0];
      const canvasPos = toCanvasCoords(currentPos.x_position, currentPos.y_position, canvas);
      
      // 1.5m detection radius circle (RFID range)
      ctx.strokeStyle = 'rgba(0, 85, 164, 0.3)';
      ctx.lineWidth = 4;
      ctx.setLineDash([16, 8]);
      const radiusCm = 150; // 1.5 meters RFID range
      const radiusPx = radiusCm * (canvas.width / STORE_WIDTH);
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
      
      // Maintain aspect ratio of STORE_WIDTH:STORE_HEIGHT (1000:800 = 1.25:1)
      const aspectRatio = STORE_WIDTH / STORE_HEIGHT;
      
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
  }, []);

  // Redraw when data changes
  useEffect(() => {
    drawMap();
    // Removed drawMissingItemsAlert - now shown in sidebar instead
  }, [anchors, positions, items, setupMode, hoveredAnchor, draggedAnchor, canvasSize, legendCollapsed]);

  // Removed auto-pulsing animation for missing items alert (now shown in sidebar)

  // Handle canvas click (place new anchor in setup mode)
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!setupMode || !onAnchorPlace) return;
    if (draggedAnchor !== null) return; // Don't place if we were dragging
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const storeCoords = toStoreCoords(x, y, canvas);
    onAnchorPlace(storeCoords.x, storeCoords.y, nextAnchorIndex);
    setNextAnchorIndex(nextAnchorIndex + 1);
  };

  // Handle mouse down (start dragging)
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!setupMode) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Check if clicking on an anchor
    for (const anchor of anchors) {
      const anchorCanvas = toCanvasCoords(anchor.x_position, anchor.y_position, canvas);
      const distance = Math.sqrt(
        Math.pow(x - anchorCanvas.x, 2) + Math.pow(y - anchorCanvas.y, 2)
      );
      
      if (distance < 15) {
        setDraggedAnchor(anchor.id);
        break;
      }
    }
  };

  // Handle mouse move (dragging)
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    if (draggedAnchor !== null && setupMode && onAnchorUpdate) {
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
      
      if (distance < 15) {
        hovering = anchor.id;
        break;
      }
    }
    setHoveredAnchor(hovering);
  };

  // Handle mouse up (stop dragging)
  const handleMouseUp = () => {
    setDraggedAnchor(null);
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
        <div className="absolute top-4 right-4 bg-[#0055A4] text-white px-4 py-2 text-sm font-medium">
          Click to place anchor #{nextAnchorIndex + 1}<br/>
          Drag existing anchors to reposition
        </div>
      )}
    </div>
  );
}
