import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

// A specialized visualization component for the "living memory" graph
const NetworkGraph = ({ memories = [], historyMap = {} }) => {
  const fgRef = useRef();
  
  // Transform memories and history into nodes and links
  const graphData = useMemo(() => {
    const nodes = [];
    const links = [];
    const addedNodes = new Set();
    
    const addNode = (mem) => {
      if (!addedNodes.has(mem.id)) {
        nodes.push({
          id: mem.id,
          name: typeof mem.content === 'string' ? mem.content.substring(0, 30) + "..." : "Memory Node",
          content: mem.content,
          val: mem.confidence || 0.5,
          color: mem.reconsolidation_flag === 'orphaned_via_surgery' ? '#555555' : 
                 mem.emotional_valence ? (mem.emotional_valence > 0 ? '#ef4444' : '#3b82f6') : '#64ffda',
          version: mem.version,
          confidence: mem.confidence,
          flag: mem.reconsolidation_flag
        });
        addedNodes.add(mem.id);
      }
    };
    
    // Add base memories
    memories.forEach(mem => {
      addNode(mem);
      // Link to parent if exists in this subset
      if (mem.parent_id && memories.find(m => m.id === mem.parent_id)) {
        links.push({
          source: mem.parent_id,
          target: mem.id,
          name: mem.update_reason || 'evolved'
        });
      }
    });
    
    // Add history memories that might not be in the direct epoch list yet
    Object.values(historyMap).forEach(histArray => {
      if (histArray && histArray.length > 0) {
        histArray.forEach((mem, index) => {
          addNode(mem);
          if (mem.parent_id) {
            links.push({
              source: mem.parent_id,
              target: mem.id,
              name: mem.update_reason || 'evolved'
            });
          }
        });
      }
    });

    return { nodes, links };
  }, [memories, historyMap]);

  return (
    <div style={{ border: '1px solid var(--border-glass)', borderRadius: '8px', overflow: 'hidden', background: '#0a192f', marginTop: '16px' }}>
      <ForceGraph2D
        ref={fgRef}
        width={860}
        height={500}
        graphData={graphData}
        nodeLabel="content"
        nodeAutoColorBy="group"
        nodeRelSize={8}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = `v${node.version}`;
          const fontSize = 12/globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); 
          
          ctx.fillStyle = node.color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, (node.val * 5) + 3, 0, 2 * Math.PI, false);
          ctx.fill();
          
          if (node.flag === 'orphaned_via_surgery') {
             // cross it out
             ctx.strokeStyle = '#ff0000';
             ctx.lineWidth = 2/globalScale;
             ctx.beginPath();
             ctx.moveTo(node.x - 5, node.y - 5);
             ctx.lineTo(node.x + 5, node.y + 5);
             ctx.stroke();
             ctx.beginPath();
             ctx.moveTo(node.x + 5, node.y - 5);
             ctx.lineTo(node.x - 5, node.y + 5);
             ctx.stroke();
          }

          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
          ctx.fillText(label, node.x, node.y + ((node.val * 5) + 8)/globalScale);
        }}
        linkColor={(link) => link.target.flag === 'orphaned_via_surgery' ? '#555' : 'rgba(100, 255, 218, 0.3)'}
        d3VelocityDecay={0.3}
      />
    </div>
  );
};

export default NetworkGraph;
