import Link from 'next/link'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { Activity, Brain, Target, Zap, Shield, TrendingUp, Heart } from 'lucide-react'

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-secondary via-secondary/95 to-primary/10">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h1 className="text-5xl md:text-7xl font-bold mb-6">
              <span className="gradient-text">NGX Agents</span>
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Transform your fitness journey with AI-powered personalized coaching from 11 specialized agents
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/register">
                <Button size="xl" variant="gradient">
                  Get Started Free
                </Button>
              </Link>
              <Link href="/about">
                <Button size="xl" variant="outline" className="text-white border-white/20 hover:bg-white/10">
                  Learn More
                </Button>
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
            <Card variant="glass" className="group hover:scale-105 transition-transform duration-300">
              <CardContent className="p-6">
                <div className="rounded-full bg-primary/20 w-12 h-12 flex items-center justify-center mb-4 group-hover:bg-primary/30 transition-colors">
                  <Target className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold text-lg mb-2 text-white">Elite Training</h3>
                <p className="text-sm text-gray-400">Personalized workout programs tailored to your goals</p>
              </CardContent>
            </Card>

            <Card variant="glass" className="group hover:scale-105 transition-transform duration-300">
              <CardContent className="p-6">
                <div className="rounded-full bg-green-500/20 w-12 h-12 flex items-center justify-center mb-4 group-hover:bg-green-500/30 transition-colors">
                  <Activity className="h-6 w-6 text-green-500" />
                </div>
                <h3 className="font-semibold text-lg mb-2 text-white">Precision Nutrition</h3>
                <p className="text-sm text-gray-400">Custom meal plans based on your needs</p>
              </CardContent>
            </Card>

            <Card variant="glass" className="group hover:scale-105 transition-transform duration-300">
              <CardContent className="p-6">
                <div className="rounded-full bg-blue-500/20 w-12 h-12 flex items-center justify-center mb-4 group-hover:bg-blue-500/30 transition-colors">
                  <Brain className="h-6 w-6 text-blue-500" />
                </div>
                <h3 className="font-semibold text-lg mb-2 text-white">Biometric Insights</h3>
                <p className="text-sm text-gray-400">Real-time health data analysis</p>
              </CardContent>
            </Card>

            <Card variant="glass" className="group hover:scale-105 transition-transform duration-300">
              <CardContent className="p-6">
                <div className="rounded-full bg-purple-500/20 w-12 h-12 flex items-center justify-center mb-4 group-hover:bg-purple-500/30 transition-colors">
                  <Zap className="h-6 w-6 text-purple-500" />
                </div>
                <h3 className="font-semibold text-lg mb-2 text-white">24/7 Support</h3>
                <p className="text-sm text-gray-400">Always available AI coaching</p>
              </CardContent>
            </Card>
          </div>

          <Card variant="gradient" className="mb-16">
            <CardContent className="p-8 md:p-12">
              <h2 className="text-3xl font-bold mb-8 text-center">11 Specialized AI Agents at Your Service</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-white/10 p-2">
                    <Target className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">Elite Training Strategist</h4>
                    <p className="text-sm text-gray-300">Designs personalized training programs</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-white/10 p-2">
                    <Activity className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">Precision Nutrition Architect</h4>
                    <p className="text-sm text-gray-300">Creates customized nutrition plans</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-white/10 p-2">
                    <Brain className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">Biometrics Insight Engine</h4>
                    <p className="text-sm text-gray-300">Analyzes health and biometric data</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-white/10 p-2">
                    <Heart className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">Motivation Behavior Coach</h4>
                    <p className="text-sm text-gray-300">Provides motivation and support</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-white/10 p-2">
                    <TrendingUp className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">Progress Tracker</h4>
                    <p className="text-sm text-gray-300">Monitors and reports progress</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="rounded-full bg-white/10 p-2">
                    <Shield className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">Recovery Corrective</h4>
                    <p className="text-sm text-gray-300">Injury prevention and recovery</p>
                  </div>
                </div>
              </div>
              <div className="text-center mt-8">
                <p className="text-sm text-gray-300 mb-4">Plus 5 more specialized agents for complete fitness transformation</p>
                <Link href="/agents">
                  <Button variant="secondary">Meet All Agents</Button>
                </Link>
              </div>
            </CardContent>
          </Card>

          <div className="text-center">
            <h2 className="text-3xl font-bold mb-4">Ready to Transform Your Fitness Journey?</h2>
            <p className="text-lg text-gray-300 mb-8">Join thousands who are already achieving their goals with NGX Agents</p>
            <Link href="/register">
              <Button size="xl" variant="gradient">
                Start Your Free Trial
              </Button>
            </Link>
          </div>
        </div>
      </div>
      <div className="absolute inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/20 rounded-full blur-3xl animate-float" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl animate-float" style={{ animationDelay: '3s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse-slow" />
      </div>
    </main>
  )
}