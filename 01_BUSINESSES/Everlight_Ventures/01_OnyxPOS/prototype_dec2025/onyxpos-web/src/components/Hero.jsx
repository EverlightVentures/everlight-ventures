export default function Hero() {
  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-dark via-darkCard to-dark">
      {/* Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 text-center">
        <div className="inline-block mb-4 px-6 py-2 bg-primary/10 border border-primary/20 rounded-full">
          <span className="text-primary font-semibold">Luxury Operating System for Business</span>
        </div>

        <h1 className="text-6xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
          OnyxOS
        </h1>

        <p className="text-xl md:text-2xl text-gray-400 mb-4 max-w-3xl mx-auto">
          OnyxPOS + OnyxPayroll in one elegant, enterprise-grade system.
        </p>

        <p className="text-lg text-gray-500 mb-12 max-w-2xl mx-auto">
          A premium, hands-off platform built for owners who demand control, compliance, and profit.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
          <a
            href="#calculator"
            className="px-8 py-4 bg-primary hover:bg-primary/80 text-white font-semibold rounded-lg transition-all text-lg shadow-lg shadow-primary/20"
          >
            See Pricing Calculator
          </a>
          <a
            href="#features"
            className="px-8 py-4 bg-darkCard hover:bg-darkCard/80 text-white font-semibold rounded-lg transition-all text-lg border-2 border-gray-700 hover:border-primary"
          >
            Explore Features
          </a>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-8 max-w-3xl mx-auto pt-16 border-t border-gray-800">
          <div>
            <div className="text-4xl font-bold text-primary mb-2">$249</div>
            <p className="text-sm text-gray-400">OnyxPOS Core</p>
          </div>
          <div>
            <div className="text-4xl font-bold text-secondary mb-2">$149</div>
            <p className="text-sm text-gray-400">OnyxPayroll Add-On</p>
          </div>
          <div>
            <div className="text-4xl font-bold text-accent mb-2">$400</div>
            <p className="text-sm text-gray-400">OnyxOS Bundle</p>
          </div>
        </div>
      </div>
    </div>
  );
}
