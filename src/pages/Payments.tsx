import PaymentProcessor from "@/components/PaymentProcessor";
import AutomatedPaymentRules from "@/components/AutomatedPaymentRules";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const Payments = () => {
  return (
    <div className="container mx-auto py-4 sm:py-8 px-4">
      <header className="mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold mb-2">Payment Processor</h1>
        <p className="text-sm sm:text-base text-muted-foreground">
          Accept payments in native CRO or ERC-20 tokens on Cronos with agentic automation
        </p>
      </header>
      <Tabs defaultValue="processor" className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-md mb-6">
          <TabsTrigger value="processor">Payment Processor</TabsTrigger>
          <TabsTrigger value="rules">Automated Rules</TabsTrigger>
        </TabsList>
        <TabsContent value="processor">
          <PaymentProcessor />
        </TabsContent>
        <TabsContent value="rules">
          <AutomatedPaymentRules />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Payments;
