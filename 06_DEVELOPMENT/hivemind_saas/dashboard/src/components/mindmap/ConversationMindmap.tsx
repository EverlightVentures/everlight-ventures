"use client";

import React, { useCallback, useMemo } from "react";
import ReactFlow, {
  Node,
  Edge,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Handle,
  Position,
  NodeProps,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { cn, getAgentColor } from "@/lib/utils";
import type { MindmapNodeData, AgentId } from "@/types";

// ============================================================
// Custom node styles by type
// ============================================================
const NODE_STYLE = {
  root: {
    background: "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)",
    border: "1px solid rgba(124,58,237,0.5)",
    color: "#F1F1F8",
    boxShadow: "0 0 30px rgba(124,58,237,0.4), 0 4px 16px rgba(0,0,0,0.5)",
  },
  agent: {
    background: "linear-gradient(135deg, #16161F 0%, #111118 100%)",
    border: "1px solid #2A2A3E",
    color: "#F1F1F8",
    boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
  },
  action: {
    background: "#111118",
    border: "1px solid #1E1E2E",
    color: "#A0A0B8",
    boxShadow: "0 1px 4px rgba(0,0,0,0.3)",
  },
  result: {
    background: "linear-gradient(135deg, rgba(16,185,129,0.1) 0%, #111118 100%)",
    border: "1px solid rgba(16,185,129,0.25)",
    color: "#34D399",
    boxShadow: "0 0 12px rgba(16,185,129,0.15)",
  },
  error: {
    background: "linear-gradient(135deg, rgba(239,68,68,0.1) 0%, #111118 100%)",
    border: "1px solid rgba(239,68,68,0.25)",
    color: "#F87171",
    boxShadow: "0 0 12px rgba(239,68,68,0.15)",
  },
} as const;

const STATUS_INDICATOR = {
  done: { color: "#10B981", label: "Done" },
  running: { color: "#7C3AED", label: "Running" },
  pending: { color: "#5C5C7A", label: "Pending" },
  failed: { color: "#EF4444", label: "Failed" },
} as const;

// ============================================================
// Custom node renderer
// ============================================================
function HiveNode({ data }: NodeProps<MindmapNodeData>) {
  const style = NODE_STYLE[data.type] ?? NODE_STYLE.action;
  const agentColor = data.agentId ? getAgentColor(data.agentId as AgentId) : null;
  const statusCfg = data.status ? STATUS_INDICATOR[data.status] : null;

  return (
    <div
      className="relative rounded-xl px-4 py-3 min-w-[140px] max-w-[220px] cursor-default"
      style={{
        ...style,
        fontFamily: "'Inter', sans-serif",
        transition: "box-shadow 0.2s ease",
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: "#2A2A3E",
          border: "2px solid #1E1E2E",
          width: 8,
          height: 8,
        }}
      />

      {/* Agent color strip for agent nodes */}
      {data.type === "agent" && agentColor && (
        <div
          className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-xl"
          style={{ background: agentColor, boxShadow: `0 0 8px ${agentColor}60` }}
        />
      )}

      <div className="flex items-start justify-between gap-2 mb-1">
        <span
          className={cn(
            "text-[12px] font-semibold leading-tight",
            data.type === "root" && "text-white text-[13px]"
          )}
        >
          {data.label}
        </span>
        {statusCfg && (
          <div
            className="flex-shrink-0 w-1.5 h-1.5 rounded-full mt-1"
            style={{
              backgroundColor: statusCfg.color,
              boxShadow: `0 0 4px ${statusCfg.color}80`,
            }}
          />
        )}
      </div>

      {data.content && (
        <p className="text-[10.5px] leading-snug mt-1 opacity-70 line-clamp-2">
          {data.content}
        </p>
      )}

      {data.tokens && data.tokens > 0 && (
        <div className="mt-2 flex items-center gap-1">
          <span
            className="text-[9px] font-semibold px-1.5 py-0.5 rounded-md"
            style={{
              background: "rgba(255,255,255,0.06)",
              color: "#5C5C7A",
            }}
          >
            {(data.tokens / 1000).toFixed(1)}k tokens
          </span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: "#2A2A3E",
          border: "2px solid #1E1E2E",
          width: 8,
          height: 8,
        }}
      />
    </div>
  );
}

const NODE_TYPES = { hiveNode: HiveNode };

// ============================================================
// Placeholder graph data
// ============================================================
const PLACEHOLDER_NODES: Node<MindmapNodeData>[] = [
  {
    id: "root",
    type: "hiveNode",
    position: { x: 0, y: 200 },
    data: {
      label: "Generate Q4 Report",
      type: "root",
      content: "Analyze sales data and produce executive summary",
      status: "running",
    },
  },
  // Claude branch
  {
    id: "claude",
    type: "hiveNode",
    position: { x: 280, y: 60 },
    data: {
      label: "Claude",
      type: "agent",
      agentId: "claude",
      content: "Strategic analysis + writing",
      status: "running",
      tokens: 14820,
    },
  },
  {
    id: "claude-action-1",
    type: "hiveNode",
    position: { x: 560, y: 0 },
    data: {
      label: "Read Drive Files",
      type: "action",
      content: "Q4_sales.xlsx, pipeline.csv",
      status: "done",
    },
  },
  {
    id: "claude-result-1",
    type: "hiveNode",
    position: { x: 560, y: 100 },
    data: {
      label: "Summary Draft",
      type: "result",
      content: "3-page executive summary generated",
      status: "done",
      tokens: 4200,
    },
  },
  // Gemini branch
  {
    id: "gemini",
    type: "hiveNode",
    position: { x: 280, y: 200 },
    data: {
      label: "Gemini",
      type: "agent",
      agentId: "gemini",
      content: "Market research + data",
      status: "running",
      tokens: 8430,
    },
  },
  {
    id: "gemini-action-1",
    type: "hiveNode",
    position: { x: 560, y: 200 },
    data: {
      label: "Web Search",
      type: "action",
      content: "Competitor Q4 benchmarks",
      status: "done",
    },
  },
  {
    id: "gemini-result-1",
    type: "hiveNode",
    position: { x: 560, y: 300 },
    data: {
      label: "Market Context",
      type: "result",
      content: "Industry comps appended to report",
      status: "done",
      tokens: 2800,
    },
  },
  // Codex branch
  {
    id: "codex",
    type: "hiveNode",
    position: { x: 280, y: 350 },
    data: {
      label: "Codex",
      type: "agent",
      agentId: "codex",
      content: "Automation + formatting",
      status: "pending",
      tokens: 0,
    },
  },
  {
    id: "codex-action-1",
    type: "hiveNode",
    position: { x: 560, y: 400 },
    data: {
      label: "Format PDF",
      type: "action",
      content: "Convert to branded PDF",
      status: "pending",
    },
  },
  {
    id: "codex-action-2",
    type: "hiveNode",
    position: { x: 560, y: 470 },
    data: {
      label: "Slack Delivery",
      type: "action",
      content: "Post to #leadership channel",
      status: "pending",
    },
  },
];

const PLACEHOLDER_EDGES: Edge[] = [
  {
    id: "root-claude",
    source: "root",
    target: "claude",
    markerEnd: { type: MarkerType.ArrowClosed, color: "#F59E0B" },
    style: { stroke: "#F59E0B60", strokeWidth: 2 },
    animated: true,
  },
  {
    id: "root-gemini",
    source: "root",
    target: "gemini",
    markerEnd: { type: MarkerType.ArrowClosed, color: "#3B82F6" },
    style: { stroke: "#3B82F660", strokeWidth: 2 },
    animated: true,
  },
  {
    id: "root-codex",
    source: "root",
    target: "codex",
    markerEnd: { type: MarkerType.ArrowClosed, color: "#10B981" },
    style: { stroke: "#10B98160", strokeWidth: 2 },
  },
  {
    id: "claude-action-1",
    source: "claude",
    target: "claude-action-1",
    style: { stroke: "#2A2A3E", strokeWidth: 1.5 },
  },
  {
    id: "claude-result-1",
    source: "claude",
    target: "claude-result-1",
    style: { stroke: "#2A2A3E", strokeWidth: 1.5 },
  },
  {
    id: "gemini-action-1",
    source: "gemini",
    target: "gemini-action-1",
    style: { stroke: "#2A2A3E", strokeWidth: 1.5 },
  },
  {
    id: "gemini-result-1",
    source: "gemini",
    target: "gemini-result-1",
    style: { stroke: "#2A2A3E", strokeWidth: 1.5 },
  },
  {
    id: "codex-action-1",
    source: "codex",
    target: "codex-action-1",
    style: { stroke: "#2A2A3E", strokeWidth: 1.5, strokeDasharray: "4 4" },
  },
  {
    id: "codex-action-2",
    source: "codex",
    target: "codex-action-2",
    style: { stroke: "#2A2A3E", strokeWidth: 1.5, strokeDasharray: "4 4" },
  },
];

// ============================================================
// Main ConversationMindmap Component
// ============================================================
interface ConversationMindmapProps {
  nodes?: Node<MindmapNodeData>[];
  edges?: Edge[];
  sessionTitle?: string;
  className?: string;
}

export default function ConversationMindmap({
  nodes: externalNodes,
  edges: externalEdges,
  sessionTitle = "Q4 Report Generation",
  className,
}: ConversationMindmapProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(externalNodes ?? PLACEHOLDER_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(externalEdges ?? PLACEHOLDER_EDGES);

  const onConnect = useCallback(
    (connection: Connection) =>
      setEdges((eds) =>
        addEdge({ ...connection, style: { stroke: "#2A2A3E", strokeWidth: 1.5 } }, eds)
      ),
    [setEdges]
  );

  const nodeTypes = useMemo(() => NODE_TYPES, []);

  return (
    <div
      className={cn("rounded-2xl overflow-hidden flex flex-col", className)}
      style={{
        background: "#0A0A0F",
        border: "1px solid #1E1E2E",
        boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 flex-shrink-0"
        style={{ borderBottom: "1px solid #1E1E2E" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-2 h-2 rounded-full"
            style={{ background: "#7C3AED", boxShadow: "0 0 8px rgba(124,58,237,0.6)" }}
          />
          <span
            className="text-[13px] font-semibold text-[#F1F1F8]"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            {sessionTitle}
          </span>
          <span className="badge badge-thinking text-[9px]">Live</span>
        </div>

        <div className="flex items-center gap-4 text-[11px] text-[#5C5C7A]">
          <span>
            <span className="text-[#A0A0B8] font-medium">{nodes.length}</span> nodes
          </span>
          <span>
            <span className="text-[#A0A0B8] font-medium">{edges.length}</span> edges
          </span>
        </div>
      </div>

      {/* Legend */}
      <div
        className="flex items-center gap-4 px-4 py-2 flex-shrink-0"
        style={{ borderBottom: "1px solid #1E1E2E", background: "rgba(0,0,0,0.2)" }}
      >
        {(
          [
            { type: "root", label: "Query", color: "#7C3AED" },
            { type: "agent", label: "Agent", color: "#A0A0B8" },
            { type: "action", label: "Action", color: "#5C5C7A" },
            { type: "result", label: "Result", color: "#10B981" },
          ] as const
        ).map((item) => (
          <div key={item.type} className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-sm"
              style={{ background: item.color }}
            />
            <span className="text-[10px] text-[#5C5C7A]">{item.label}</span>
          </div>
        ))}
      </div>

      {/* Flow canvas */}
      <div className="flex-1" style={{ height: "520px" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          attributionPosition="bottom-right"
          proOptions={{ hideAttribution: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={24}
            size={1}
            color="#1E1E2E"
          />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              const data = node.data as MindmapNodeData;
              if (data.type === "root") return "#7C3AED";
              if (data.agentId) return getAgentColor(data.agentId as AgentId);
              if (data.type === "result") return "#10B981";
              return "#2A2A3E";
            }}
            style={{ background: "#111118", border: "1px solid #1E1E2E" }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
