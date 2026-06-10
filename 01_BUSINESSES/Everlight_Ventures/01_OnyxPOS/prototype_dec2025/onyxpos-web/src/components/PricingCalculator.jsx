export default function PricingCalculator() {
  return (
    <div className="py-24 bg-darkCard" id="calculator">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">
            OnyxPOS Pricing
          </h2>
          <p className="text-xl text-gray-400">
            Transparent pricing that grows with you. Subscription + platform fees.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-8">
          {/* Core Plan */}
          <div className="bg-dark border-2 border-gray-700 rounded-2xl p-8 hover:border-primary transition-all">
            <div className="bg-primary text-white px-4 py-2 rounded-lg inline-block mb-4 font-semibold">
              Core
            </div>
            <p className="text-sm text-gray-400 mb-6">For new businesses getting started</p>
            <div className="mb-6">
              <div className="text-5xl font-bold mb-2">
                $119<span className="text-xl text-gray-400 font-normal">/mo</span>
              </div>
              <p className="text-sm text-gray-400">+ platform fees</p>
            </div>

            {/* Platform Fees Breakdown */}
            <div className="bg-gray-800 rounded-lg p-4 mb-6">
              <div className="text-sm font-semibold mb-2">Platform Fees:</div>
              <div className="text-xs text-gray-400 space-y-1">
                <div>• 10% on first $10k/mo</div>
                <div>• 5% on $10k-$50k/mo</div>
                <div>• 1% over $50k/mo</div>
                <div className="text-yellow-400 mt-2">Min: $1,000/mo total</div>
              </div>
            </div>

            <div className="space-y-2 text-sm text-gray-400 mb-6">
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>2 devices, team of 6</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Auto-SKU generation</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Task management</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Auto shift scheduling</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>FIFO/COGS tracking</span>
              </div>
            </div>

            {/* Example Calculation */}
            <div className="bg-gray-900 rounded-lg p-3 mb-6 text-xs">
              <div className="font-semibold mb-1">Example at $15k/mo sales:</div>
              <div className="text-gray-400">$119 + $1,250 fee = <span className="text-green-400">$1,369/mo</span></div>
            </div>

            <button className="w-full bg-primary hover:bg-primary/80 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
              Start 14-Day Trial
            </button>
          </div>

          {/* Growth Plan */}
          <div className="bg-dark border-2 border-secondary rounded-2xl p-8 relative">
            <div className="absolute top-0 right-0 bg-secondary text-white px-3 py-1 rounded-bl-lg text-xs font-bold">
              POPULAR
            </div>
            <div className="bg-secondary text-white px-4 py-2 rounded-lg inline-block mb-4 font-semibold">
              Growth
            </div>
            <p className="text-sm text-gray-400 mb-6">For established small businesses</p>
            <div className="mb-6">
              <div className="text-5xl font-bold mb-2">
                $249<span className="text-xl text-gray-400 font-normal">/mo</span>
              </div>
              <p className="text-sm text-gray-400">+ platform fees</p>
            </div>

            {/* Platform Fees Breakdown */}
            <div className="bg-gray-800 rounded-lg p-4 mb-6">
              <div className="text-sm font-semibold mb-2">Platform Fees:</div>
              <div className="text-xs text-gray-400 space-y-1">
                <div>• 10% on first $10k/mo</div>
                <div>• 5% on $10k-$50k/mo</div>
                <div>• 1% over $50k/mo</div>
                <div className="text-yellow-400 mt-2">Min: $1,000/mo total</div>
              </div>
            </div>

            <div className="space-y-2 text-sm text-gray-400 mb-6">
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span className="font-semibold">Everything in Core +</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>6 devices, team of 15</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Shopify integration</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Square payments</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Gusto payroll sync</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>QuickBooks sync</span>
              </div>
            </div>

            {/* Example Calculation */}
            <div className="bg-gray-900 rounded-lg p-3 mb-6 text-xs">
              <div className="font-semibold mb-1">Example at $30k/mo sales:</div>
              <div className="text-gray-400">$249 + $2,000 fee = <span className="text-green-400">$2,249/mo</span></div>
            </div>

            <button className="w-full bg-secondary hover:bg-secondary/80 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
              Start 14-Day Trial
            </button>
          </div>

          {/* Prime Plan */}
          <div className="bg-dark border-2 border-accent rounded-2xl p-8">
            <div className="bg-accent text-white px-4 py-2 rounded-lg inline-block mb-4 font-semibold">
              Prime
            </div>
            <p className="text-sm text-gray-400 mb-6">For high-volume businesses</p>
            <div className="mb-6">
              <div className="text-5xl font-bold mb-2">
                $399<span className="text-xl text-gray-400 font-normal">/mo</span>
              </div>
              <p className="text-sm text-gray-400">+ platform fees</p>
            </div>

            {/* Platform Fees Breakdown */}
            <div className="bg-gray-800 rounded-lg p-4 mb-6">
              <div className="text-sm font-semibold mb-2">Platform Fees:</div>
              <div className="text-xs text-gray-400 space-y-1">
                <div>• 10% on first $10k/mo</div>
                <div>• 5% on $10k-$50k/mo</div>
                <div>• 1% over $50k/mo</div>
                <div className="text-yellow-400 mt-2">Min: $1,000/mo total</div>
              </div>
            </div>

            <div className="space-y-2 text-sm text-gray-400 mb-6">
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span className="font-semibold">Everything in Growth +</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Unlimited devices & team</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>DoorDash integration</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>UberEats integration</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Grubhub integration</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>OnyxAI assistant</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                <span>Priority support</span>
              </div>
            </div>

            {/* Example Calculation */}
            <div className="bg-gray-900 rounded-lg p-3 mb-6 text-xs">
              <div className="font-semibold mb-1">Example at $75k/mo sales:</div>
              <div className="text-gray-400">$399 + $3,250 fee = <span className="text-green-400">$3,649/mo</span></div>
            </div>

            <button className="w-full bg-accent hover:bg-accent/80 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
              Contact Sales
            </button>
          </div>
        </div>

        {/* Platform Fee Details */}
        <div className="mt-16 bg-dark border-2 border-gray-700 rounded-2xl p-8">
          <h3 className="text-2xl font-bold mb-6 text-center">How Platform Fees Work</h3>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Left: Explanation */}
            <div>
              <p className="text-gray-400 mb-4">
                Platform fees are calculated based on your monthly sales volume (GMV - Gross Merchandise Value).
              </p>
              <p className="text-gray-400 mb-4">
                The fee tier decreases as your sales increase:
              </p>
              <ul className="space-y-2 text-gray-400 text-sm">
                <li>• First $10,000 in monthly sales = 10% fee</li>
                <li>• Sales from $10,001 to $50,000 = 5% fee</li>
                <li>• All sales over $50,000 = 1% fee</li>
              </ul>
              <p className="text-yellow-400 mt-4 text-sm">
                Minimum platform fee is $1,000/month regardless of sales volume.
              </p>
            </div>

            {/* Right: Example Calculations */}
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="font-semibold mb-4">Example Calculations:</div>
              <div className="space-y-4 text-sm">
                <div>
                  <div className="font-semibold text-white">$5,000/mo in sales:</div>
                  <div className="text-gray-400">$5,000 × 10% = $500</div>
                  <div className="text-yellow-400">Minimum fee applies: $1,000</div>
                  <div className="text-green-400 mt-1">Core: $119 + $1,000 = $1,119/mo</div>
                </div>

                <div>
                  <div className="font-semibold text-white">$25,000/mo in sales:</div>
                  <div className="text-gray-400">First $10k × 10% = $1,000</div>
                  <div className="text-gray-400">Next $15k × 5% = $750</div>
                  <div className="text-green-400 mt-1">Growth: $249 + $1,750 = $1,999/mo</div>
                </div>

                <div>
                  <div className="font-semibold text-white">$100,000/mo in sales:</div>
                  <div className="text-gray-400">First $10k × 10% = $1,000</div>
                  <div className="text-gray-400">Next $40k × 5% = $2,000</div>
                  <div className="text-gray-400">Last $50k × 1% = $500</div>
                  <div className="text-green-400 mt-1">Prime: $399 + $3,500 = $3,899/mo</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-16 text-center">
          <h3 className="text-2xl font-bold mb-6">Frequently Asked Questions</h3>
          <div className="grid md:grid-cols-2 gap-6 text-left">
            <div className="bg-dark border border-gray-700 rounded-lg p-6">
              <h4 className="font-semibold mb-2">Why platform fees instead of per-transaction fees?</h4>
              <p className="text-sm text-gray-400">
                Traditional POS systems charge 2-3% per transaction. Our tiered model means you pay less as you grow. At $100k/mo, you only pay 3.5% total vs Square's 2.6% + 10¢ per transaction.
              </p>
            </div>

            <div className="bg-dark border border-gray-700 rounded-lg p-6">
              <h4 className="font-semibold mb-2">Can I switch plans anytime?</h4>
              <p className="text-sm text-gray-400">
                Yes! Upgrade or downgrade anytime. Your platform fees stay the same regardless of plan tier.
              </p>
            </div>

            <div className="bg-dark border border-gray-700 rounded-lg p-6">
              <h4 className="font-semibold mb-2">What's included in the 14-day trial?</h4>
              <p className="text-sm text-gray-400">
                Full access to all features in your chosen plan. No credit card required. No platform fees during trial.
              </p>
            </div>

            <div className="bg-dark border border-gray-700 rounded-lg p-6">
              <h4 className="font-semibold mb-2">Do I need to pay for integrations separately?</h4>
              <p className="text-sm text-gray-400">
                No! All integrations (Shopify, Square, Gusto, QuickBooks) are included. You just bring your own accounts with those services.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
