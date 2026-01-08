import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

export default function Settings() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground">Configure your CLEO preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>App Preferences</CardTitle>
          <CardDescription>Theme, date formats, developer toggles</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="mev">MEV Protection</Label>
            <Switch id="mev" defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="auto-route">Auto Re-route</Label>
            <Switch id="auto-route" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
          <CardDescription>MCP API key, x402 facilitator address, agent settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="mcp-key">MCP API Key</Label>
            <Input id="mcp-key" placeholder="Enter your MCP API key" type="password" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="facilitator">x402 Facilitator Address</Label>
            <Input id="facilitator" placeholder="0x..." />
          </div>
          <Button>Save Changes</Button>
        </CardContent>
      </Card>
    </div>
  );
}
