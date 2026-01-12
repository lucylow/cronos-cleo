import PaymentProcessor from "@/components/PaymentProcessor";

const Payments = () => {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Payment Processor</h1>
        <p className="text-muted-foreground">
          Accept payments in native CRO or ERC-20 tokens on Cronos
        </p>
      </div>
      <PaymentProcessor />
    </div>
  );
};

export default Payments;
