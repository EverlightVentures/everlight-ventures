const features = [
  {
    icon: '💳',
    title: 'Multi-Payment Support',
    description: 'Accept cash, card, and crypto with lightning-fast checkout.',
  },
  {
    icon: '📱',
    title: 'Native Mobile Apps',
    description: 'iOS and Android apps for managing your store on the go.',
  },
  {
    icon: '📊',
    title: 'Real-Time Analytics',
    description: 'Owner-level dashboards for profit, labor, and inventory health.',
  },
  {
    icon: '📦',
    title: 'Inventory Management',
    description: 'FIFO/COGS tracking, smart reorders, and vendor-ready insights.',
  },
  {
    icon: '👥',
    title: 'OnyxPayroll',
    description: 'Gusto integration for payroll - automates time tracking and syncs hours seamlessly.',
  },
  {
    icon: '🔐',
    title: 'Secure & Compliant',
    description: 'Bank-grade security with PCI compliance and encrypted data.',
  },
  {
    icon: '🔧',
    title: 'Self-Diagnosing',
    description: 'Automated issue detection and resolution with built-in diagnostics.',
  },
  {
    icon: '⚡',
    title: 'Lightning Fast',
    description: 'Process transactions in milliseconds with optimized performance.',
  },
  {
    icon: '🌐',
    title: 'Multi-Tenant SaaS',
    description: 'Complete tenant isolation with secure, scalable architecture.',
  },
  {
    icon: '📈',
    title: 'Growth Automation',
    description: 'Task routing, reorder triggers, and performance nudges.',
  },
];

export default function Features() {
  return (
    <div className="py-24 bg-dark" id="features">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Everything You Need
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            A unified system built for owners who want clarity, control, and profit.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="bg-darkCard border-2 border-gray-800 hover:border-primary rounded-2xl p-8 transition-all hover:scale-105"
            >
              <div className="text-5xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
              <p className="text-gray-400">{feature.description}</p>
            </div>
          ))}
        </div>

        {/* Comparison */}
        <div className="mt-24 bg-darkCard border-2 border-gray-800 rounded-2xl p-12">
          <h3 className="text-3xl font-bold mb-8 text-center">
            OnyxOS vs. Traditional Stacks
          </h3>
          <div className="grid md:grid-cols-2 gap-12">
            <div>
              <h4 className="text-2xl font-bold text-red-400 mb-6">Traditional Stack</h4>
              <ul className="space-y-4">
                <li className="flex items-start gap-3">
                  <span className="text-red-400 text-xl">✗</span>
                  <span className="text-gray-400">Multiple tools stitched together with weak reporting</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-red-400 text-xl">✗</span>
                  <span className="text-gray-400">Manual hours entry to payroll providers</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-red-400 text-xl">✗</span>
                  <span className="text-gray-400">Inventory blind spots and late reorders</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-red-400 text-xl">✗</span>
                  <span className="text-gray-400">Disjointed support with no owner intelligence</span>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-2xl font-bold text-primary mb-6">OnyxOS</h4>
              <ul className="space-y-4">
                <li className="flex items-start gap-3">
                  <span className="text-green-400 text-xl">✓</span>
                  <span className="text-gray-300 font-medium">Unified POS + Payroll + Inventory + Tasks</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-green-400 text-xl">✓</span>
                  <span className="text-gray-300 font-medium">Automated hours sync to your Gusto account</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-green-400 text-xl">✓</span>
                  <span className="text-gray-300 font-medium">FIFO/COGS clarity and owner-grade margins</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-green-400 text-xl">✓</span>
                  <span className="text-gray-300 font-medium">Works on any device with a luxury, simple UI</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
