export default function CTA() {
  return (
    <div className="py-24 bg-gradient-to-br from-primary/20 via-darkCard to-secondary/20">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-4xl md:text-5xl font-bold mb-6">
          Ready to Switch?
        </h2>
        <p className="text-xl text-gray-300 mb-8">
          Join the owners building calmer, more profitable businesses.
        </p>
        <p className="text-lg text-gray-400 mb-12">
          OnyxOS bundles POS + Payroll into one premium system for <span className="text-primary font-bold">$400/mo</span>.
          Annual contract required with a 10% prepay discount available.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button className="px-8 py-4 bg-primary hover:bg-primary/80 text-white font-semibold rounded-lg transition-all text-lg shadow-lg shadow-primary/20">
            Start Free Trial
          </button>
          <button className="px-8 py-4 bg-darkCard hover:bg-dark text-white font-semibold rounded-lg transition-all text-lg border-2 border-gray-700 hover:border-primary">
            Schedule Demo
          </button>
        </div>

        <p className="mt-8 text-sm text-gray-500">
          Owner onboarding in 7–14 days • Compliance handled • Contracts reviewed by counsel
        </p>
      </div>
    </div>
  );
}
