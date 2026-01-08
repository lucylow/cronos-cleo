import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Cpu, Activity, Clock, CheckCircle } from 'lucide-react';

export default function Agent() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">AI Agent</h1>
        <p className="text-muted-foreground">Intelligent routing decisions powered by Crypto.com AI Agent SDK</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <Cpu className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold text-green-500">Online</div>
            <p className="text-xs text-muted-foreground">Agent ready for decisions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Decisions Today</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">127</div>
            <p className="text-xs text-muted-foreground">Routing optimizations</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Avg Response</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">145ms</div>
            <p className="text-xs text-muted-foreground">Decision latency</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Decisions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Split route: VVS 60% / CronaSwap 40%</p>
                  <p className="text-xs text-muted-foreground">100,000 CRO → USDC.e • 2.1% savings</p>
                </div>
                <span className="text-xs text-muted-foreground">2m ago</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
