'use client'

import { useAuth } from '@/contexts/AuthContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { Activity, Brain, Target, TrendingUp, Heart, Zap } from 'lucide-react'

export default function DashboardPage() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          <Skeleton className="h-10 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardHeader className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-6 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">
          Welcome back, {user?.name || 'Athlete'}!
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Here&apos;s your fitness journey overview
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Streak</CardTitle>
            <Target className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12 days</div>
            <p className="text-xs text-muted-foreground">+2 from last week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Calories Burned</CardTitle>
            <Activity className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2,450</div>
            <p className="text-xs text-muted-foreground">This week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Workouts</CardTitle>
            <Zap className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5/7</div>
            <p className="text-xs text-muted-foreground">This week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recovery Score</CardTitle>
            <Heart className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">85%</div>
            <p className="text-xs text-muted-foreground">Optimal</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Today&apos;s Plan</CardTitle>
            <CardDescription>Your scheduled activities for today</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-primary/10 rounded-lg">
              <div className="flex items-center gap-4">
                <div className="rounded-full bg-primary/20 p-2">
                  <Activity className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h4 className="font-semibold">Upper Body Strength</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">45 minutes • 8:00 AM</p>
                </div>
              </div>
              <Badge variant="success">Completed</Badge>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-4">
                <div className="rounded-full bg-green-500/20 p-2">
                  <Brain className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <h4 className="font-semibold">Nutrition Check-in</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">10 minutes • 12:00 PM</p>
                </div>
              </div>
              <Badge>Upcoming</Badge>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-4">
                <div className="rounded-full bg-purple-500/20 p-2">
                  <Heart className="h-5 w-5 text-purple-500" />
                </div>
                <div>
                  <h4 className="font-semibold">Evening Recovery</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">20 minutes • 8:00 PM</p>
                </div>
              </div>
              <Badge>Scheduled</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Agents</CardTitle>
            <CardDescription>Your AI coaching team</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-primary/20 p-2">
                <Target className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Elite Training Strategist</p>
                <p className="text-xs text-gray-500">Optimizing your workouts</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="rounded-full bg-green-500/20 p-2">
                <Activity className="h-4 w-4 text-green-500" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Nutrition Architect</p>
                <p className="text-xs text-gray-500">Tracking your macros</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="rounded-full bg-blue-500/20 p-2">
                <Brain className="h-4 w-4 text-blue-500" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Biometrics Engine</p>
                <p className="text-xs text-gray-500">Analyzing health data</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="rounded-full bg-purple-500/20 p-2">
                <TrendingUp className="h-4 w-4 text-purple-500" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Progress Tracker</p>
                <p className="text-xs text-gray-500">Monitoring improvements</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}