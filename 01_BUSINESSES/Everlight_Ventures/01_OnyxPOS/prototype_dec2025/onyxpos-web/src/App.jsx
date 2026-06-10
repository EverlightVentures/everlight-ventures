import Hero from './components/Hero'
import Features from './components/Features'
import PricingCalculator from './components/PricingCalculator'
import CTA from './components/CTA'
import Footer from './components/Footer'

function App() {
  return (
    <div className="min-h-screen bg-dark text-white">
      <Hero />
      <Features />
      <PricingCalculator />
      <CTA />
      <Footer />
    </div>
  )
}

export default App
