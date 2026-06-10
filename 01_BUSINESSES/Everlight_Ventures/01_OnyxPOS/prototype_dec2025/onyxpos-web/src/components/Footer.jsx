export default function Footer() {
  return (
    <footer className="bg-dark border-t border-gray-800 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-3 gap-8 mb-8">
          <div>
            <h3 className="text-2xl font-bold mb-4 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              OnyxOS
            </h3>
            <p className="text-gray-400 text-sm">
              Premium point of sale with owner intelligence.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Product</h4>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><a href="#features" className="hover:text-primary transition-colors">Features</a></li>
              <li><a href="#calculator" className="hover:text-primary transition-colors">Pricing</a></li>
              <li><a href="https://app.onyxpos.com" className="hover:text-primary transition-colors">Login</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Support</h4>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><a href="mailto:support@onyxpos.com" className="hover:text-primary transition-colors">Email Support</a></li>
              <li><a href="https://github.com/yourusername/onyxpos/issues" className="hover:text-primary transition-colors">Report Issue</a></li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-gray-800 text-center">
          <p className="text-gray-500 text-sm">
            © 2025 OnyxOS. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
