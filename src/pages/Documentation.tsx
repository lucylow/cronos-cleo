import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  BookOpen,
  FileText,
  Code,
  Zap,
  Shield,
  ArrowRight,
  ExternalLink,
  HelpCircle,
  Video,
  MessageSquare,
} from 'lucide-react';
import { Separator } from '@/components/ui/separator';

const quickStartSteps = [
  {
    title: 'Connect Wallet',
    description: 'Connect your wallet to start using C.L.E.O.',
    icon: Shield,
  },
  {
    title: 'Configure Settings',
    description: 'Set up your preferences and gas settings',
    icon: Zap,
  },
  {
    title: 'Execute Swap',
    description: 'Choose tokens and execute your first swap',
    icon: ArrowRight,
  },
];

const documentationSections = [
  {
    title: 'Getting Started',
    description: 'Learn the basics of using C.L.E.O.',
    icon: BookOpen,
    topics: ['Introduction', 'Wallet Setup', 'First Swap', 'Understanding Routes'],
  },
  {
    title: 'Features',
    description: 'Explore all available features',
    icon: Zap,
    topics: ['Multi-DEX Routing', 'AI Agent', 'Settlement', 'Payments'],
  },
  {
    title: 'API Reference',
    description: 'Developer documentation and APIs',
    icon: Code,
    topics: ['REST API', 'WebSocket', 'SDK', 'Examples'],
  },
  {
    title: 'Security',
    description: 'Security best practices',
    icon: Shield,
    topics: ['Audits', 'Smart Contracts', 'Best Practices', 'FAQ'],
  },
];

const faqItems = [
  {
    question: 'How does C.L.E.O. find the best routes?',
    answer:
      'C.L.E.O. uses advanced algorithms and AI to analyze multiple DEXes simultaneously, finding optimal routes that minimize slippage and gas costs while maximizing output.',
  },
  {
    question: 'What fees does C.L.E.O. charge?',
    answer:
      'C.L.E.O. charges a small protocol fee on successful swaps. The exact fee varies based on the transaction size and complexity. All fees are transparent and shown before execution.',
  },
  {
    question: 'Is C.L.E.O. safe to use?',
    answer:
      'Yes, C.L.E.O. uses audited smart contracts and follows security best practices. Your funds are never held by C.L.E.O. - swaps execute directly on the blockchain.',
  },
  {
    question: 'Which DEXes does C.L.E.O. support?',
    answer:
      'C.L.E.O. supports major Cronos DEXes including VVS Finance, Cronaswap, MM Finance, Tectonic, and more. The list is constantly expanding.',
  },
];

export default function Documentation() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Documentation</h1>
        <p className="text-muted-foreground mt-1">
          Learn how to use C.L.E.O. effectively
        </p>
      </div>

      <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Quick Start Guide
          </CardTitle>
          <CardDescription>
            Get up and running with C.L.E.O. in minutes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {quickStartSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={index} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">
                      {index + 1}
                    </div>
                    <Icon className="h-4 w-4 text-primary" />
                  </div>
                  <h3 className="font-semibold">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.description}</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="guides">Guides</TabsTrigger>
          <TabsTrigger value="api">API</TabsTrigger>
          <TabsTrigger value="faq">FAQ</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {documentationSections.map((section) => {
              const Icon = section.icon;
              return (
                <Card key={section.title} className="hover:border-primary/50 transition-colors">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Icon className="h-5 w-5 text-primary" />
                      <CardTitle>{section.title}</CardTitle>
                    </div>
                    <CardDescription>{section.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {section.topics.map((topic) => (
                        <li key={topic} className="flex items-center gap-2 text-sm">
                          <ArrowRight className="h-3 w-3 text-muted-foreground" />
                          <span>{topic}</span>
                        </li>
                      ))}
                    </ul>
                    <Button variant="outline" className="w-full mt-4" size="sm">
                      View Section
                      <ExternalLink className="h-3 w-3 ml-2" />
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="guides" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Step-by-Step Guides</CardTitle>
              <CardDescription>Detailed guides for common tasks</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  {
                    title: 'Getting Started with C.L.E.O.',
                    description: 'A complete walkthrough for new users',
                    duration: '5 min read',
                    category: 'Getting Started',
                  },
                  {
                    title: 'Optimizing Gas Costs',
                    description: 'Learn how to minimize gas fees on your swaps',
                    duration: '3 min read',
                    category: 'Optimization',
                  },
                  {
                    title: 'Using the AI Agent',
                    description: 'Master the AI-powered route optimization',
                    duration: '7 min read',
                    category: 'Features',
                  },
                  {
                    title: 'Multi-Leg Settlements',
                    description: 'Understanding and using settlement pipelines',
                    duration: '10 min read',
                    category: 'Advanced',
                  },
                ].map((guide, index) => (
                  <div
                    key={index}
                    className="flex items-start justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <h3 className="font-semibold">{guide.title}</h3>
                        <Badge variant="secondary" className="text-xs">
                          {guide.category}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{guide.description}</p>
                      <span className="text-xs text-muted-foreground">{guide.duration}</span>
                    </div>
                    <Button variant="ghost" size="sm">
                      Read
                      <ArrowRight className="h-3 w-3 ml-1" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API Documentation</CardTitle>
              <CardDescription>Developer resources and API references</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Code className="h-4 w-4" />
                      REST API
                    </h3>
                    <Badge>v1.0</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    HTTP API for integrating C.L.E.O. into your applications
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      View Docs
                      <ExternalLink className="h-3 w-3 ml-2" />
                    </Button>
                    <Button variant="outline" size="sm">
                      API Key
                    </Button>
                  </div>
                </div>

                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Zap className="h-4 w-4" />
                      WebSocket API
                    </h3>
                    <Badge>Real-time</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    Real-time updates and notifications via WebSocket
                  </p>
                  <Button variant="outline" size="sm">
                    View Docs
                    <ExternalLink className="h-3 w-3 ml-2" />
                  </Button>
                </div>

                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Code className="h-4 w-4" />
                      JavaScript SDK
                    </h3>
                    <Badge>npm</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    Official SDK for JavaScript/TypeScript projects
                  </p>
                  <div className="bg-muted p-2 rounded font-mono text-sm mb-3">
                    npm install @cleo/sdk
                  </div>
                  <Button variant="outline" size="sm">
                    View Docs
                    <ExternalLink className="h-3 w-3 ml-2" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="faq" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HelpCircle className="h-5 w-5" />
                Frequently Asked Questions
              </CardTitle>
              <CardDescription>Common questions and answers</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {faqItems.map((item, index) => (
                  <div key={index}>
                    <h3 className="font-semibold mb-2">{item.question}</h3>
                    <p className="text-sm text-muted-foreground">{item.answer}</p>
                    {index < faqItems.length - 1 && <Separator className="mt-4" />}
                  </div>
                ))}
              </div>
              <div className="mt-6 p-4 border rounded-lg bg-muted/50">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare className="h-4 w-4" />
                  <h3 className="font-semibold">Still have questions?</h3>
                </div>
                <p className="text-sm text-muted-foreground mb-3">
                  Reach out to our support team or join our community
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    Contact Support
                  </Button>
                  <Button variant="outline" size="sm">
                    Join Discord
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}


