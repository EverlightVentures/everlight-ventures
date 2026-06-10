export default function Loading() {
  return (
    <div className="space-y-6 animate-pulse">
      <div>
        <div className="h-3 w-28 bg-ash rounded" />
        <div className="h-10 w-96 bg-graphite rounded mt-3" />
        <div className="h-4 w-72 bg-ash/60 rounded mt-3" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-card-gradient border border-ash rounded-xl px-4 py-4 h-24" />
        ))}
      </div>
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-card-gradient border border-ash rounded-xl h-60" />
        <div className="bg-card-gradient border border-ash rounded-xl h-60" />
      </div>
      <div className="bg-card-gradient border border-ash rounded-xl h-96" />
    </div>
  );
}
