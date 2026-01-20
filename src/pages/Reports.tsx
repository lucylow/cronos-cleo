import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { Download, Calendar as CalendarIcon, TrendingUp, DollarSign, Activity, FileText } from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const monthlyReport = {
  period: 'January 2024',
  totalVolume: 328000,
  totalExecutions: 1734,
  totalProfit: 13780,
  totalSavings: 14560,
  avgSavingsPct: 4.2,
  totalGasCost: 1240,
  totalFees: 820,
  netProfit: 11720,
  transactions: [
    { date: 'Week 1', volume: 78000, profit: 3200, executions: 412 },
    { date: 'Week 2', volume: 82000, profit: 3500, executions: 435 },
    { date: 'Week 3', volume: 89000, profit: 3800, executions: 452 },
    { date: 'Week 4', volume: 79000, profit: 3280, executions: 435 },
  ],
  dexBreakdown: [
    { name: 'VVS Finance', volume: 114800, percentage: 35, count: 607 },
    { name: 'Cronaswap', volume: 91840, percentage: 28, count: 486 },
    { name: 'MM Finance', volume: 72160, percentage: 22, count: 381 },
    { name: 'Tectonic', volume: 32800, percentage: 10, count: 173 },
    { name: 'Other', volume: 16400, percentage: 5, count: 87 },
  ],
  topPerformers: [
    { token: 'CRO/USDT', volume: 45000, profit: 1890, savings: 6.2 },
    { token: 'WBTC/ETH', volume: 32000, profit: 1344, savings: 5.8 },
    { token: 'USDC/DAI', volume: 28000, profit: 1176, savings: 5.5 },
  ],
};

export default function Reports() {
  const [dateRange, setDateRange] = useState<{ from?: Date; to?: Date }>({});
  const [reportType, setReportType] = useState('monthly');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground mt-1">
            Generate and download detailed performance reports
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={reportType} onValueChange={setReportType}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekly">Weekly</SelectItem>
              <SelectItem value="monthly">Monthly</SelectItem>
              <SelectItem value="yearly">Yearly</SelectItem>
            </SelectContent>
          </Select>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline">
                <CalendarIcon className="h-4 w-4 mr-2" />
                {dateRange.from ? format(dateRange.from, 'MMM dd') : 'Date range'}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar
                mode="range"
                selected={{ from: dateRange.from, to: dateRange.to }}
                onSelect={(range) => setDateRange(range || {})}
                numberOfMonths={2}
              />
            </PopoverContent>
          </Popover>
          <Button>
            <Download className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Volume</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${(monthlyReport.totalVolume / 1000).toFixed(1)}K
            </div>
            <p className="text-xs text-muted-foreground mt-1">{monthlyReport.period}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Net Profit</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              ${(monthlyReport.netProfit / 1000).toFixed(1)}K
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              ROI: {((monthlyReport.netProfit / monthlyReport.totalVolume) * 100).toFixed(2)}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Savings</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${(monthlyReport.totalSavings / 1000).toFixed(1)}K
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Avg: {monthlyReport.avgSavingsPct}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Executions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{monthlyReport.totalExecutions}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {Math.round(monthlyReport.totalExecutions / 30)} per day
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="dex">DEX Breakdown</TabsTrigger>
          <TabsTrigger value="detailed">Detailed</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Volume & Profit Trends</CardTitle>
                <CardDescription>Weekly breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{ volume: { label: 'Volume ($)' }, profit: { label: 'Profit ($)' } }}>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={monthlyReport.transactions}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="date" className="text-xs" />
                      <YAxis yAxisId="left" className="text-xs" />
                      <YAxis yAxisId="right" orientation="right" className="text-xs" />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Bar yAxisId="left" dataKey="volume" fill="#0088FE" name="Volume ($)" />
                      <Bar yAxisId="right" dataKey="profit" fill="#00C49F" name="Profit ($)" />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Financial Summary</CardTitle>
                <CardDescription>Revenue and costs breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Total Profit</span>
                      <span className="font-semibold">${monthlyReport.totalProfit.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Total Savings</span>
                      <span className="font-semibold text-green-500">
                        ${monthlyReport.totalSavings.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="border-t pt-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Gas Costs</span>
                      <span className="font-semibold text-red-500">
                        -${monthlyReport.totalGasCost.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Protocol Fees</span>
                      <span className="font-semibold text-red-500">
                        -${monthlyReport.totalFees.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="border-t pt-4">
                    <div className="flex justify-between">
                      <span className="font-semibold">Net Profit</span>
                      <span className="text-2xl font-bold text-green-500">
                        ${monthlyReport.netProfit.toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Weekly Performance</CardTitle>
              <CardDescription>Volume and profit over time</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={{ volume: { label: 'Volume ($)' }, profit: { label: 'Profit ($)' } }}>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={monthlyReport.transactions}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" className="text-xs" />
                    <YAxis yAxisId="left" className="text-xs" />
                    <YAxis yAxisId="right" orientation="right" className="text-xs" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="volume"
                      stroke="#0088FE"
                      strokeWidth={2}
                      name="Volume ($)"
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="profit"
                      stroke="#00C49F"
                      strokeWidth={2}
                      name="Profit ($)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </ChartContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top Performing Pairs</CardTitle>
              <CardDescription>Highest volume and profit token pairs</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {monthlyReport.topPerformers.map((pair, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <div className="font-semibold">{pair.token}</div>
                      <div className="text-sm text-muted-foreground">
                        Volume: ${pair.volume.toLocaleString()}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-green-500">+${pair.profit.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground">Savings: {pair.savings}%</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dex" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>DEX Distribution</CardTitle>
                <CardDescription>Volume distribution by DEX</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}}>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={monthlyReport.dexBreakdown}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ percentage }) => `${percentage}%`}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="percentage"
                      >
                        {monthlyReport.dexBreakdown.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>DEX Statistics</CardTitle>
                <CardDescription>Detailed breakdown by exchange</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {monthlyReport.dexBreakdown.map((dex, index) => (
                    <div key={dex.name} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          <span className="font-medium">{dex.name}</span>
                        </div>
                        <span className="text-muted-foreground">
                          ${(dex.volume / 1000).toFixed(1)}K ({dex.percentage}%)
                        </span>
                      </div>
                      <div className="w-full bg-secondary rounded-full h-2">
                        <div
                          className="h-2 rounded-full transition-all"
                          style={{
                            width: `${dex.percentage}%`,
                            backgroundColor: COLORS[index % COLORS.length],
                          }}
                        />
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {dex.count} executions
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="detailed" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Detailed Report</CardTitle>
              <CardDescription>Complete financial breakdown for {monthlyReport.period}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div>
                  <h3 className="font-semibold mb-3">Revenue</h3>
                  <div className="space-y-2 pl-4">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Trading Profit</span>
                      <span className="font-medium">${monthlyReport.totalProfit.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total Savings</span>
                      <span className="font-medium text-green-500">
                        ${monthlyReport.totalSavings.toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold mb-3">Costs</h3>
                  <div className="space-y-2 pl-4">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Gas Costs</span>
                      <span className="font-medium text-red-500">
                        -${monthlyReport.totalGasCost.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Protocol Fees</span>
                      <span className="font-medium text-red-500">
                        -${monthlyReport.totalFees.toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-semibold">Net Profit</span>
                    <span className="text-2xl font-bold text-green-500">
                      ${monthlyReport.netProfit.toLocaleString()}
                    </span>
                  </div>
                  <div className="text-sm text-muted-foreground mt-2">
                    ROI: {((monthlyReport.netProfit / monthlyReport.totalVolume) * 100).toFixed(2)}%
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold mb-3">Key Metrics</h3>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <div className="text-sm text-muted-foreground">Total Volume</div>
                      <div className="text-xl font-semibold">
                        ${monthlyReport.totalVolume.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Total Executions</div>
                      <div className="text-xl font-semibold">{monthlyReport.totalExecutions}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Average Savings</div>
                      <div className="text-xl font-semibold">{monthlyReport.avgSavingsPct}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Profit per Execution</div>
                      <div className="text-xl font-semibold">
                        ${(monthlyReport.netProfit / monthlyReport.totalExecutions).toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

