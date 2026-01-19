/**
 * Automated Payment Rules - Agentic Payment Features
 * Allows users to create rules for automatic payment processing
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Switch } from './ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Textarea } from './ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Alert, AlertDescription } from './ui/alert';
import { Plus, Trash2, Zap, CheckCircle2, XCircle } from 'lucide-react';
import { toast } from 'sonner';

interface PaymentRule {
  id: string;
  name: string;
  enabled: boolean;
  condition: {
    type: 'amount' | 'sender' | 'token' | 'risk_score' | 'time';
    operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte' | 'contains';
    value: string;
  };
  action: {
    type: 'auto_approve' | 'auto_reject' | 'flag' | 'notify';
    params?: Record<string, any>;
  };
  priority: number;
  createdAt: number;
  lastExecuted?: number;
  executionCount: number;
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function AutomatedPaymentRules() {
  const [rules, setRules] = useState<PaymentRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState<PaymentRule | null>(null);

  const [formData, setFormData] = useState<Partial<PaymentRule>>({
    name: '',
    enabled: true,
    condition: {
      type: 'amount',
      operator: 'gt',
      value: '',
    },
    action: {
      type: 'auto_approve',
    },
    priority: 1,
  });

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = () => {
    const stored = localStorage.getItem('automatedPaymentRules');
    if (stored) {
      try {
        setRules(JSON.parse(stored));
      } catch (e) {
        console.error('Failed to load rules:', e);
      }
    }
  };

  const saveRules = (newRules: PaymentRule[]) => {
    setRules(newRules);
    localStorage.setItem('automatedPaymentRules', JSON.stringify(newRules));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name || !formData.condition?.value) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (editingRule) {
      // Update existing rule
      const updated = rules.map(r =>
        r.id === editingRule.id
          ? { ...formData, id: editingRule.id, createdAt: editingRule.createdAt, executionCount: editingRule.executionCount } as PaymentRule
          : r
      );
      saveRules(updated);
      toast.success('Rule updated successfully');
    } else {
      // Create new rule
      const newRule: PaymentRule = {
        id: `rule_${Date.now()}`,
        name: formData.name!,
        enabled: formData.enabled ?? true,
        condition: formData.condition!,
        action: formData.action!,
        priority: formData.priority || 1,
        createdAt: Date.now(),
        executionCount: 0,
      };
      saveRules([...rules, newRule]);
      toast.success('Rule created successfully');
    }

    // Reset form
    setFormData({
      name: '',
      enabled: true,
      condition: { type: 'amount', operator: 'gt', value: '' },
      action: { type: 'auto_approve' },
      priority: 1,
    });
    setShowForm(false);
    setEditingRule(null);
  };

  const deleteRule = (id: string) => {
    saveRules(rules.filter(r => r.id !== id));
    toast.success('Rule deleted');
  };

  const toggleRule = (id: string) => {
    saveRules(rules.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));
    toast.success('Rule toggled');
  };

  const startEdit = (rule: PaymentRule) => {
    setEditingRule(rule);
    setFormData(rule);
    setShowForm(true);
  };

  const cancelEdit = () => {
    setShowForm(false);
    setEditingRule(null);
    setFormData({
      name: '',
      enabled: true,
      condition: { type: 'amount', operator: 'gt', value: '' },
      action: { type: 'auto_approve' },
      priority: 1,
    });
  };

  // Simulate rule execution (in production, this would be handled by backend)
  const evaluateRule = (rule: PaymentRule, payment: any): boolean => {
    if (!rule.enabled) return false;

    const { condition } = rule;
    let matches = false;

    switch (condition.type) {
      case 'amount':
        const paymentAmount = BigInt(payment.amount);
        const ruleAmount = BigInt(condition.value);
        matches =
          condition.operator === 'gt' ? paymentAmount > ruleAmount :
          condition.operator === 'lt' ? paymentAmount < ruleAmount :
          condition.operator === 'eq' ? paymentAmount === ruleAmount :
          condition.operator === 'gte' ? paymentAmount >= ruleAmount :
          condition.operator === 'lte' ? paymentAmount <= ruleAmount :
          false;
        break;
      case 'sender':
        matches = payment.payer.toLowerCase().includes(condition.value.toLowerCase());
        break;
      case 'risk_score':
        const score = payment.risk_score || 0;
        const ruleScore = parseFloat(condition.value);
        matches =
          condition.operator === 'gt' ? score > ruleScore :
          condition.operator === 'lt' ? score < ruleScore :
          condition.operator === 'eq' ? score === ruleScore :
          condition.operator === 'gte' ? score >= ruleScore :
          condition.operator === 'lte' ? score <= ruleScore :
          false;
        break;
      default:
        matches = false;
    }

    return matches;
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Automated Payment Rules</CardTitle>
              <CardDescription>
                Create rules to automatically process payments based on conditions
              </CardDescription>
            </div>
            <Button onClick={() => setShowForm(!showForm)}>
              <Plus className="w-4 h-4 mr-2" />
              {showForm ? 'Cancel' : 'New Rule'}
            </Button>
          </div>
        </CardHeader>

        {showForm && (
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Rule Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Auto-approve small payments"
                  />
                </div>
                <div>
                  <Label htmlFor="priority">Priority (1-10)</Label>
                  <Input
                    id="priority"
                    type="number"
                    min="1"
                    max="10"
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 1 })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="conditionType">Condition Type</Label>
                  <Select
                    value={formData.condition?.type}
                    onValueChange={(value: any) =>
                      setFormData({
                        ...formData,
                        condition: { ...formData.condition!, type: value, operator: 'gt', value: '' },
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="amount">Amount</SelectItem>
                      <SelectItem value="sender">Sender Address</SelectItem>
                      <SelectItem value="risk_score">Risk Score</SelectItem>
                      <SelectItem value="token">Token</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="operator">Operator</Label>
                  <Select
                    value={formData.condition?.operator}
                    onValueChange={(value: any) =>
                      setFormData({
                        ...formData,
                        condition: { ...formData.condition!, operator: value },
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gt">&gt; (Greater Than)</SelectItem>
                      <SelectItem value="lt">&lt; (Less Than)</SelectItem>
                      <SelectItem value="eq">= (Equals)</SelectItem>
                      <SelectItem value="gte">≥ (Greater or Equal)</SelectItem>
                      <SelectItem value="lte">≤ (Less or Equal)</SelectItem>
                      <SelectItem value="contains">Contains</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="value">Value *</Label>
                  <Input
                    id="value"
                    value={formData.condition?.value}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        condition: { ...formData.condition!, value: e.target.value },
                      })
                    }
                    placeholder={
                      formData.condition?.type === 'amount'
                        ? 'Amount in wei'
                        : formData.condition?.type === 'risk_score'
                        ? '0-10'
                        : 'Value'
                    }
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="action">Action</Label>
                <Select
                  value={formData.action?.type}
                  onValueChange={(value: any) =>
                    setFormData({
                      ...formData,
                      action: { type: value },
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto_approve">Auto Approve</SelectItem>
                    <SelectItem value="auto_reject">Auto Reject</SelectItem>
                    <SelectItem value="flag">Flag for Review</SelectItem>
                    <SelectItem value="notify">Send Notification</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="enabled"
                  checked={formData.enabled}
                  onCheckedChange={(checked) => setFormData({ ...formData, enabled: checked })}
                />
                <Label htmlFor="enabled">Rule Enabled</Label>
              </div>

              <div className="flex gap-2">
                <Button type="submit">{editingRule ? 'Update Rule' : 'Create Rule'}</Button>
                {editingRule && (
                  <Button type="button" variant="outline" onClick={cancelEdit}>
                    Cancel
                  </Button>
                )}
              </div>
            </form>
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active Rules ({rules.filter(r => r.enabled).length})</CardTitle>
          <CardDescription>
            Rules are evaluated in priority order. Higher priority rules are checked first.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {rules.length === 0 ? (
            <Alert>
              <AlertDescription>No rules configured. Create your first rule to get started.</AlertDescription>
            </Alert>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Condition</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Executions</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules
                  .sort((a, b) => b.priority - a.priority)
                  .map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell className="font-medium">{rule.name}</TableCell>
                      <TableCell>
                        <code className="text-xs">
                          {rule.condition.type} {rule.condition.operator} {rule.condition.value}
                        </code>
                      </TableCell>
                      <TableCell>
                        <Badge variant={rule.action.type === 'auto_approve' ? 'default' : 'destructive'}>
                          {rule.action.type.replace('_', ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell>{rule.priority}</TableCell>
                      <TableCell>{rule.executionCount}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {rule.enabled ? (
                            <CheckCircle2 className="w-4 h-4 text-green-500" />
                          ) : (
                            <XCircle className="w-4 h-4 text-gray-400" />
                          )}
                          <span className="text-sm">{rule.enabled ? 'Enabled' : 'Disabled'}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleRule(rule.id)}
                          >
                            <Zap className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => startEdit(rule)}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => deleteRule(rule.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
