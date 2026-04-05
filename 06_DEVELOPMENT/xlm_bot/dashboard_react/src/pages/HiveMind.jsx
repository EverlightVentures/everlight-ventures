import React from "react"

export default function HiveMind() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold bg-gradient-to-r from-amber-300 to-amber-500 bg-clip-text text-transparent">
        Hive Mind
      </h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="card text-center py-6">
          <div className="text-3xl font-bold text-amber-400">63</div>
          <div className="text-sm text-gray-500">Agents</div>
        </div>
        <div className="card text-center py-6">
          <div className="text-3xl font-bold text-amber-400">12</div>
          <div className="text-sm text-gray-500">Fire Teams</div>
        </div>
        <div className="card text-center py-6">
          <div className="text-3xl font-bold text-amber-400">4</div>
          <div className="text-sm text-gray-500">Squads</div>
        </div>
      </div>
      <div className="card">
        <div className="text-center py-8 text-gray-500">Agent roster and status coming soon</div>
      </div>
    </div>
  )
}
