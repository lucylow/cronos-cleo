import { Header } from "@/components/Header";
import { HeroSection } from "@/components/HeroSection";
import { DemoSection } from "@/components/DemoSection";
import { FeaturesSection } from "@/components/FeaturesSection";
import { HowItWorksSection } from "@/components/HowItWorksSection";
import { Footer } from "@/components/Footer";

const Index = () => {
  return (
    <main className="min-h-screen bg-background">
      <Header />
      <HeroSection />
      <DemoSection />
      <FeaturesSection />
      <HowItWorksSection />
      <Footer />
    </main>
  );
};

export default Index;
