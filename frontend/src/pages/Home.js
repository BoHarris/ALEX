import ApiSection from "../components/home/ApiSection";
import CallToActionSection from "../components/home/CallToActionSection";
import CapabilitiesSection from "../components/home/CapabilitiesSection";
import HeroSection from "../components/home/HeroSection";
import HowItWorksSection from "../components/home/HowItWorksSection";
import ProblemSection from "../components/home/ProblemSection";
import ProductPreviewSection from "../components/home/ProductPreviewSection";
import SecuritySection from "../components/home/SecuritySection";

export default function Home() {
  return (
    <div className="page-shell px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-24 pb-16">
        <HeroSection />
        <ProblemSection />
        <HowItWorksSection />
        <CapabilitiesSection />
        <ProductPreviewSection />
        <ApiSection />
        <SecuritySection />
        <CallToActionSection />
      </div>
    </div>
  );
}
