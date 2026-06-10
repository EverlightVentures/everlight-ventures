import React, { useMemo } from "react"
import { useApi, timeAgo } from "../hooks"

const COLUMNS = [
  { key: "todo", label: "Todo", color: "border-gray-500", headerBg: "bg-gray-500/10", headerText: "text-gray-400" },
  { key: "in_progress", label: "In Progress", color: "border-blue-400", headerBg: "bg-blue-400/10", headerText: "text-blue-400" },
  { key: "review", label: "Review", color: "border-amber-400", headerBg: "bg-amber-400/10", headerText: "text-amber-400" },
  { key: "done", label: "Done", color: "border-green-400", headerBg: "bg-green-400/10", headerText: "text-green-400" },
]

const PRIORITY_STYLES = {
  high: "bg-amber-400/10 text-amber-400 border-amber-400/30",
  medium: "bg-blue-400/10 text-blue-300 border-blue-400/30",
  low: "bg-gray-400/10 text-gray-400 border-gray-400/30",
  critical: "bg-red-400/10 text-red-300 border-red-400/30",
}

function TaskCard({ task }) {
  const priorityStyle = PRIORITY_STYLES[task.priority] || PRIORITY_STYLES.medium
  const isOverdue = task.due_date && new Date(task.due_date) < new Date()

  return (
    <div className="bg-[#111] border border-[#222] rounded-lg p-3 hover:border-white/[0.08] transition-colors">
      <div className="flex items-start justify-between mb-2">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide border ${priorityStyle}`}>
          {task.priority || "medium"}
        </span>
        {task.due_date && (
          <span className={`text-[9px] font-mono ${isOverdue ? "text-red-400" : "text-gray-500"}`}>
            {isOverdue ? "OVERDUE" : new Date(task.due_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
          </span>
        )}
      </div>
      <div className="text-[11px] text-gray-200 font-medium mb-2">{task.title || "Untitled Task"}</div>
      {task.description && <div className="text-[10px] text-gray-500 mb-2 line-clamp-2">{task.description}</div>}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-4 rounded-full bg-amber-400/20 flex items-center justify-center text-[8px] text-amber-400 font-bold">
            {(task.assignee || "?").charAt(0).toUpperCase()}
          </div>
          <span className="text-[9px] text-gray-500">{task.assignee || "Unassigned"}</span>
        </div>
        {task.created_at && <span className="text-[9px] text-gray-600">{timeAgo(task.created_at)}</span>}
      </div>
    </div>
  )
}

export default function Taskboard() {
  const { data, error } = useApi("/api/django/taskboard", 15000)

  const tasks = data?.tasks || data || []
  const taskList = Array.isArray(tasks) ? tasks : []

  const grouped = useMemo(() => {
    const g = { todo: [], in_progress: [], review: [], done: [] }
    taskList.forEach(t => {
      const status = (t.status || "todo").toLowerCase().replace(/ /g, "_")
      if (g[status]) g[status].push(t)
      else g.todo.push(t)
    })
    return g
  }, [taskList])

  const openCount = grouped.todo.length
  const progressCount = grouped.in_progress.length
  const todayDone = grouped.done.filter(t => {
    if (!t.completed_at && !t.updated_at) return false
    const d = new Date(t.completed_at || t.updated_at)
    return d.toDateString() === new Date().toDateString()
  }).length
  const blockedCount = taskList.filter(t => t.blocked || t.priority === "critical").length

  if (!data && !error) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card"><div className="h-2 w-12 bg-white/[0.05] rounded mb-2" /><div className="h-6 w-16 bg-white/[0.08] rounded" /></div>
          ))}
        </div>
        <div className="card h-64 flex items-center justify-center"><div className="text-[10px] text-gray-600 tracking-widest">Loading Taskboard...</div></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-amber-400 tracking-wider">TASKBOARD</h1>
          <p className="text-xs text-gray-500 mt-1">Hive Task Management</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${error ? "bg-red-400" : "bg-green-400"} animate-pulse`} />
          <span className="text-[9px] text-gray-500 font-mono">15s refresh</span>
        </div>
      </div>

      {error && (
        <div className="card border border-red-400/20 bg-red-400/[0.03]">
          <div className="text-[10px] text-red-400">API connection issue</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{error}</div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Open</div>
          <div className="font-mono text-2xl font-bold text-white">{openCount}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">In Progress</div>
          <div className="font-mono text-2xl font-bold text-blue-400">{progressCount}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Completed Today</div>
          <div className="font-mono text-2xl font-bold text-green-400">{todayDone}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Blocked</div>
          <div className="font-mono text-2xl font-bold text-red-400">{blockedCount}</div>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {COLUMNS.map(col => (
          <div key={col.key} className="space-y-2">
            <div className={`flex items-center justify-between px-3 py-2 rounded-lg ${col.headerBg} border-t-2 ${col.color}`}>
              <span className={`text-[10px] uppercase tracking-wider font-semibold ${col.headerText}`}>{col.label}</span>
              <span className="text-[10px] text-gray-500 font-mono">{grouped[col.key].length}</span>
            </div>
            <div className="space-y-2 min-h-[200px]">
              {grouped[col.key].length === 0 ? (
                <div className="text-center py-8 text-[10px] text-gray-700">No tasks</div>
              ) : (
                grouped[col.key].map((task, i) => <TaskCard key={task.id || i} task={task} />)
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
