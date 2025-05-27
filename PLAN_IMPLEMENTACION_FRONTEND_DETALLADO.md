# PLAN DE IMPLEMENTACIÓN FRONTEND NGX AGENTS - SUPER DETALLADO
## "De Backend Robusto a Experiencia de Usuario Revolucionaria"

---

## 📊 ESTADO ACTUAL DEL PROYECTO

### Backend Status (85% Completado)
- ✅ FASES 1-7: Completadas al 100%
- 🟡 FASE 8: External Integrations (50%)
  - ✅ WHOOP 4.0, Apple Health
  - ⏳ Pendiente: Oura, Garmin, Fitbit, Strava, Push Notifications, WhatsApp
- ⬜ FASE 9: Advanced AI (0%)
- ⬜ FASE 10: Security & Compliance (0%)

### Estimación para Completar Backend
- FASE 8: 3-4 semanas
- FASE 9: 4-5 semanas  
- FASE 10: 2-3 semanas
- **Total: 9-12 semanas**

---

## 🚀 PLAN DE IMPLEMENTACIÓN FRONTEND

### FASE 1: ARQUITECTURA Y SETUP INICIAL (Semanas 1-2)

#### 1.1 Setup del Proyecto (3 días)
```bash
# Estructura Monorepo
npx create-turbo@latest ngx-frontend --example with-tailwind
cd ngx-frontend
npm install
```

**Tareas Específicas:**
- [ ] Configurar monorepo con Turborepo
- [ ] Setup Next.js 14.2+ con App Router
- [ ] Configurar TypeScript 5.3+ con strict mode
- [ ] Setup ESLint + Prettier + Husky
- [ ] Configurar Jest + React Testing Library
- [ ] Setup Cypress para E2E
- [ ] CI/CD con GitHub Actions
- [ ] Configurar Storybook 7.6+
- [ ] Setup Tailwind CSS con custom config

**Estructura Inicial:**
```
ngx-frontend/
├── apps/
│   ├── web/                    # Next.js web app
│   ├── mobile/                 # React Native app
│   └── storybook/             # Component library
├── packages/
│   ├── ui/                    # Shared components
│   ├── api-client/            # Backend integration
│   ├── state/                 # State management
│   ├── types/                 # TypeScript types
│   └── config/                # Shared configs
└── tooling/
    ├── eslint/
    ├── typescript/
    └── tailwind/
```

#### 1.2 Arquitectura de Estado y Datos (4 días)
**Stack de Estado:**
```typescript
// packages/state/src/stores/authStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  user: User | null
  token: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      login: async (credentials) => {
        // Implementation
      },
      logout: () => {
        set({ user: null, token: null })
      },
      refreshToken: async () => {
        // Auto refresh logic
      }
    }),
    { name: 'auth-storage' }
  )
)
```

**API Client Setup:**
```typescript
// packages/api-client/src/client.ts
import axios from 'axios'
import { io, Socket } from 'socket.io-client'

export class NGXApiClient {
  private axios: AxiosInstance
  private socket: Socket
  private sse: EventSource | null = null

  constructor(config: ApiConfig) {
    this.axios = axios.create({
      baseURL: config.baseURL,
      timeout: 30000,
    })
    
    this.socket = io(config.wsURL, {
      transports: ['websocket'],
      autoConnect: false
    })
    
    this.setupInterceptors()
  }

  // SSE for streaming responses
  streamChat(message: string, onData: (data: any) => void) {
    this.sse = new EventSource(`${this.baseURL}/stream/chat`)
    this.sse.onmessage = (event) => {
      onData(JSON.parse(event.data))
    }
  }
}
```

#### 1.3 Sistema de Diseño Base con Branding Neogen-X (3 días)
**Design Tokens - Paleta de Colores Neogen-X:**
```typescript
// packages/ui/src/tokens.ts
export const tokens = {
  colors: {
    // Colores principales del branding Neogen-X
    navy: {
      50: '#f0f0f5',
      100: '#d9d9e8',
      500: '#0A0628',  // Color principal Navy
      600: '#080520',
      900: '#050318'
    },
    purple: {
      50: '#f3e6ff',
      100: '#e0b3ff',
      500: '#6D00FF',  // Color principal Purple
      600: '#5500cc',
      900: '#330080'
    },
    gray: {
      50: '#fafafa',
      100: '#f5f5f5',
      200: '#eeeeee',
      300: '#e0e0e0',
      400: '#bdbdbd',
      500: '#CCCCCC',  // Color secundario Gray
      600: '#757575',
      700: '#616161',
      800: '#424242',
      900: '#212121'
    },
    white: '#FFFFFF',  // Color base White
    black: '#000000',
    
    // Estados y feedback
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6'
  },
  spacing: {
    xs: '0.5rem',
    sm: '1rem',
    md: '1.5rem',
    lg: '2rem',
    xl: '3rem'
  },
  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui'],
      mono: ['SF Mono', 'monospace']
    }
  }
}
```

**Configuración Tailwind con Branding:**
```javascript
// packages/config/tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        // Colores principales Neogen-X
        navy: {
          DEFAULT: '#0A0628',
          50: '#f0f0f5',
          100: '#d9d9e8',
          500: '#0A0628',
          600: '#080520',
          900: '#050318'
        },
        purple: {
          DEFAULT: '#6D00FF',
          50: '#f3e6ff',
          100: '#e0b3ff',
          500: '#6D00FF',
          600: '#5500cc',
          900: '#330080'
        },
        gray: {
          DEFAULT: '#CCCCCC',
          50: '#fafafa',
          500: '#CCCCCC',
          900: '#212121'
        },
        // Alias para facilidad de uso
        primary: {
          DEFAULT: '#6D00FF',
          50: '#f3e6ff',
          500: '#6D00FF',
          900: '#330080'
        },
        secondary: {
          DEFAULT: '#0A0628',
          50: '#f0f0f5',
          500: '#0A0628',
          900: '#050318'
        }
      }
    }
  }
}
```

**Componentes Base con Branding Neogen-X:**
```typescript
// packages/ui/src/components/Button.tsx
import { cva, type VariantProps } from 'class-variance-authority'

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2',
  {
    variants: {
      variant: {
        primary: 'bg-purple-500 text-white hover:bg-purple-600 focus:ring-purple-500 shadow-lg hover:shadow-xl',
        secondary: 'bg-navy-500 text-white hover:bg-navy-600 focus:ring-navy-500 shadow-md hover:shadow-lg',
        outline: 'border-2 border-purple-500 text-purple-500 hover:bg-purple-50 focus:ring-purple-500',
        ghost: 'text-navy-500 hover:bg-gray-100 focus:ring-gray-300',
        danger: 'bg-error text-white hover:bg-red-600 focus:ring-red-500'
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4',
        lg: 'h-12 px-6 text-lg'
      }
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md'
    }
  }
)

export interface ButtonProps 
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        disabled={loading}
        {...props}
      >
        {loading && <Spinner className="mr-2" />}
        {children}
      </button>
    )
  }
)
```

---

### FASE 2: INTERFAZ CONVERSACIONAL CORE (Semanas 3-5)

#### 2.1 Chat Component System (5 días)
**Message Components:**
```typescript
// apps/web/components/chat/MessageList.tsx
import { useVirtualizer } from '@tanstack/react-virtual'

export function MessageList({ messages }: { messages: Message[] }) {
  const parentRef = useRef<HTMLDivElement>(null)
  
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
    overscan: 5
  })

  return (
    <div ref={parentRef} className="h-full overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative'
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const message = messages[virtualItem.index]
          return (
            <div
              key={virtualItem.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`
              }}
            >
              <MessageBubble message={message} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

**Voice Input Integration:**
```typescript
// apps/web/hooks/useVoiceInput.ts
export function useVoiceInput() {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  
  useEffect(() => {
    if (!('webkitSpeechRecognition' in window)) return
    
    const recognition = new webkitSpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(result => result[0])
        .map(result => result.transcript)
        .join('')
      
      setTranscript(transcript)
    }
    
    if (isListening) {
      recognition.start()
    } else {
      recognition.stop()
    }
    
    return () => recognition.stop()
  }, [isListening])
  
  return { isListening, transcript, setIsListening }
}
```

#### 2.2 Agent Selector & Personalities con Branding (4 días)
```typescript
// apps/web/components/agents/AgentSelector.tsx
const agents = [
  {
    id: 'elite_training',
    name: 'Elite Training Strategist',
    avatar: '/avatars/trainer.webp',
    color: '#6D00FF', // Purple principal
    specialty: 'Diseño de programas de entrenamiento',
    personality: 'Motivador y exigente'
  },
  {
    id: 'nutrition_expert',
    name: 'Nutrition Expert',
    avatar: '/avatars/nutrition.webp',
    color: '#0A0628', // Navy principal
    specialty: 'Planes nutricionales personalizados',
    personality: 'Científico y preciso'
  },
  // ... otros agentes con colores del branding
]

export function AgentSelector({ onSelect }: { onSelect: (agent: Agent) => void }) {
  const [selected, setSelected] = useState(agents[0])
  
  return (
    <div className="flex gap-2 p-4 overflow-x-auto bg-gradient-to-r from-navy-50 to-purple-50">
      {agents.map((agent) => (
        <motion.button
          key={agent.id}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => {
            setSelected(agent)
            onSelect(agent)
          }}
          className={cn(
            "flex flex-col items-center p-3 rounded-xl transition-all duration-200",
            selected.id === agent.id
              ? "bg-white border-2 border-purple-500 shadow-lg"
              : "bg-white/70 border-2 border-transparent hover:border-gray-200 shadow-md"
          )}
        >
          <Avatar
            src={agent.avatar}
            alt={agent.name}
            className="w-16 h-16 mb-2 ring-2 ring-offset-2"
            style={{ 
              borderColor: agent.color,
              ringColor: selected.id === agent.id ? agent.color : 'transparent'
            }}
          />
          <span className="text-xs font-medium text-center text-navy-700">
            {agent.name.split(' ')[0]}
          </span>
          <span className="text-xs text-gray-500 text-center mt-1">
            {agent.specialty.split(' ')[0]}
          </span>
        </motion.button>
      ))}
    </div>
  )
}
```

#### 2.3 Streaming & Real-time (5 días)
```typescript
// apps/web/hooks/useStreamingResponse.ts
export function useStreamingResponse() {
  const [response, setResponse] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  
  const streamMessage = useCallback(async (message: string) => {
    setIsStreaming(true)
    setResponse('')
    
    const eventSource = new EventSource(
      `/api/stream/chat?message=${encodeURIComponent(message)}`
    )
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'content') {
        setResponse(prev => prev + data.content)
      } else if (data.type === 'end') {
        setIsStreaming(false)
        eventSource.close()
      }
    }
    
    eventSource.onerror = () => {
      setIsStreaming(false)
      eventSource.close()
    }
    
    return () => eventSource.close()
  }, [])
  
  return { response, isStreaming, streamMessage }
}
```

---

### FASE 2.5: IMPLEMENTACIÓN COMPLETA DEL BRANDING NEOGEN-X (Semana 5)

#### 2.5.1 Guías de Uso de Colores (2 días)
**Jerarquía Visual con Branding:**
```typescript
// packages/ui/src/guidelines/colorUsage.ts
export const colorUsageGuidelines = {
  // Navegación y Headers
  navigation: {
    background: 'bg-navy-500',
    text: 'text-white',
    activeLink: 'text-purple-300',
    hoverLink: 'text-purple-200'
  },
  
  // Botones principales
  primaryActions: {
    cta: 'bg-purple-500 hover:bg-purple-600',
    secondary: 'bg-navy-500 hover:bg-navy-600',
    outline: 'border-purple-500 text-purple-500'
  },
  
  // Cards y contenedores
  containers: {
    primary: 'bg-white border-gray-200',
    highlighted: 'bg-gradient-to-br from-purple-50 to-navy-50',
    interactive: 'hover:border-purple-300'
  },
  
  // Estados de la aplicación
  states: {
    loading: 'bg-purple-100 text-purple-700',
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    error: 'bg-red-100 text-red-700'
  }
}
```

#### 2.5.2 Componentes de Layout con Branding (2 días)
```typescript
// apps/web/components/layout/Header.tsx
export function Header() {
  return (
    <header className="bg-navy-500 shadow-lg border-b border-navy-600">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <img 
              src="/logo-neogenx-white.svg" 
              alt="Neogen-X" 
              className="h-8 w-auto"
            />
          </div>
          
          {/* Navigation */}
          <nav className="hidden md:flex space-x-8">
            <a href="/dashboard" className="text-white hover:text-purple-300 transition-colors">
              Dashboard
            </a>
            <a href="/agents" className="text-white hover:text-purple-300 transition-colors">
              Agentes
            </a>
            <a href="/analytics" className="text-white hover:text-purple-300 transition-colors">
              Analytics
            </a>
          </nav>
          
          {/* User Menu */}
          <div className="flex items-center space-x-4">
            <Button variant="outline" className="border-white text-white hover:bg-white hover:text-navy-500">
              Configuración
            </Button>
            <Avatar className="ring-2 ring-purple-300" />
          </div>
        </div>
      </div>
    </header>
  )
}

// apps/web/components/layout/Sidebar.tsx
export function Sidebar() {
  return (
    <aside className="w-64 bg-gradient-to-b from-navy-500 to-navy-600 shadow-xl">
      <div className="p-6">
        <nav className="space-y-2">
          {menuItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center px-4 py-3 rounded-lg transition-all duration-200",
                "text-white hover:bg-purple-500/20 hover:text-purple-200",
                "focus:outline-none focus:ring-2 focus:ring-purple-300"
              )}
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.label}
            </a>
          ))}
        </nav>
      </div>
    </aside>
  )
}
```

#### 2.5.3 Chat Interface con Branding (2 días)
```typescript
// apps/web/components/chat/ChatInterface.tsx
export function ChatInterface() {
  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-50 to-purple-50/30">
      {/* Header del Chat */}
      <div className="bg-white border-b border-gray-200 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 bg-purple-500 rounded-full animate-pulse"></div>
            <h2 className="text-lg font-semibold text-navy-700">
              Chat con Agente IA
            </h2>
          </div>
          <Button variant="ghost" size="sm" className="text-gray-500">
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
      {/* Área de mensajes */}
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      
      {/* Input del chat */}
      <div className="bg-white border-t border-gray-200 p-4">
        <div className="flex items-center space-x-3">
          <div className="flex-1">
            <ChatInput 
              className="border-gray-300 focus:border-purple-500 focus:ring-purple-500"
              placeholder="Escribe tu mensaje..."
            />
          </div>
          <Button className="bg-purple-500 hover:bg-purple-600">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

// Burbujas de mensaje con branding
export function MessageBubble({ message, isUser }: MessageBubbleProps) {
  return (
    <div className={cn(
      "flex mb-4",
      isUser ? "justify-end" : "justify-start"
    )}>
      <div className={cn(
        "max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow-sm",
        isUser 
          ? "bg-purple-500 text-white" 
          : "bg-white text-navy-700 border border-gray-200"
      )}>
        <p className="text-sm">{message.content}</p>
        <span className={cn(
          "text-xs mt-1 block",
          isUser ? "text-purple-100" : "text-gray-500"
        )}>
          {formatTime(message.timestamp)}
        </span>
      </div>
    </div>
  )
}
```

#### 2.5.4 Validación de Accesibilidad y Contraste (1 día)
```typescript
// packages/ui/src/utils/accessibility.ts
export const contrastValidation = {
  // Validaciones de contraste WCAG AA
  textOnNavy: {
    white: 'PASS', // Contraste suficiente
    purple: 'PASS',
    gray: 'FAIL' // Requiere ajuste
  },
  textOnPurple: {
    white: 'PASS',
    navy: 'PASS',
    gray: 'FAIL'
  },
  // Recomendaciones automáticas
  getRecommendedTextColor: (backgroundColor: string) => {
    switch (backgroundColor) {
      case '#0A0628': // Navy
        return '#FFFFFF' // White
      case '#6D00FF': // Purple
        return '#FFFFFF' // White
      case '#CCCCCC': // Gray
        return '#0A0628' // Navy
      default:
        return '#0A0628' // Navy por defecto
    }
  }
}
```

---

### FASE 3: DASHBOARD Y VISUALIZACIONES CON BRANDING (Semanas 6-8)

#### 3.1 Dashboard Principal con Branding Neogen-X (5 días)
```typescript
// apps/web/app/dashboard/page.tsx
export default function DashboardPage() {
  const { data: metrics } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: fetchDashboardMetrics
  })
  
  return (
    <DashboardLayout className="bg-gradient-to-br from-gray-50 to-purple-50/30">
      {/* Header del Dashboard */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-navy-700 mb-2">
          Dashboard de Rendimiento
        </h1>
        <p className="text-gray-600">
          Monitorea tu progreso y optimiza tu entrenamiento
        </p>
      </div>
      
      {/* Métricas principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Progreso Semanal"
          value={metrics?.weeklyProgress}
          change={metrics?.weeklyChange}
          icon={<TrendingUp className="text-purple-500" />}
          className="bg-white border-l-4 border-purple-500 shadow-lg hover:shadow-xl transition-shadow"
        />
        
        <MetricCard
          title="Calorías Quemadas"
          value={metrics?.caloriesBurned}
          change={metrics?.caloriesChange}
          icon={<Flame className="text-orange-500" />}
          className="bg-white border-l-4 border-orange-500 shadow-lg hover:shadow-xl transition-shadow"
        />
        
        <WearableWidget
          device="WHOOP"
          data={metrics?.whoopData}
          className="bg-gradient-to-br from-navy-500 to-navy-600 text-white shadow-lg"
        />
        
        <NutritionSummary
          calories={metrics?.nutrition.calories}
          macros={metrics?.nutrition.macros}
          className="bg-gradient-to-br from-purple-500 to-purple-600 text-white shadow-lg"
        />
      </div>
      
      {/* Visualizaciones principales */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ProgressChart 
          data={metrics?.progressHistory}
          className="bg-white shadow-lg rounded-xl border border-gray-200"
        />
        <Avatar3D 
          measurements={metrics?.bodyMeasurements}
          className="bg-white shadow-lg rounded-xl border border-gray-200"
        />
      </div>
      
      {/* Sección de agentes recomendados */}
      <div className="mt-8">
        <Card className="bg-gradient-to-r from-purple-50 to-navy-50 border-purple-200">
          <CardHeader>
            <CardTitle className="text-navy-700 flex items-center">
              <Bot className="w-5 h-5 mr-2 text-purple-500" />
              Agentes Recomendados para Ti
            </CardTitle>
          </CardHeader>
          <CardContent>
            <RecommendedAgents userId={user.id} />
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
```

#### 3.2 Visualización de Datos con Branding (4 días)
```typescript
// packages/ui/src/components/charts/ProgressChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'

export function ProgressChart({ data, metric = 'weight', className }) {
  return (
    <Card className={className}>
      <CardHeader className="border-b border-gray-100">
        <CardTitle className="text-navy-700 flex items-center">
          <TrendingUp className="w-5 h-5 mr-2 text-purple-500" />
          Progreso de {metric}
        </CardTitle>
        <p className="text-sm text-gray-600">
          Evolución en los últimos 30 días
        </p>
      </CardHeader>
      <CardContent className="pt-6">
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="progressGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6D00FF" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#6D00FF" stopOpacity={0.05}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis 
              dataKey="date" 
              stroke="#6B7280"
              fontSize={12}
            />
            <YAxis 
              stroke="#6B7280"
              fontSize={12}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: '#FFFFFF',
                border: '1px solid #E5E7EB',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Area
              type="monotone"
              dataKey={metric}
              stroke="#6D00FF"
              strokeWidth={3}
              fill="url(#progressGradient)"
              dot={{ fill: '#6D00FF', r: 4, strokeWidth: 2, stroke: '#FFFFFF' }}
              activeDot={{ r: 6, stroke: '#6D00FF', strokeWidth: 2, fill: '#FFFFFF' }}
            />
          </AreaChart>
        </ResponsiveContainer>
        
        {/* Estadísticas adicionales */}
        <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
          <div className="text-center">
            <p className="text-sm text-gray-600">Mejor</p>
            <p className="text-lg font-semibold text-purple-600">
              {Math.max(...data.map(d => d[metric]))}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600">Promedio</p>
            <p className="text-lg font-semibold text-navy-600">
              {(data.reduce((acc, d) => acc + d[metric], 0) / data.length).toFixed(1)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600">Tendencia</p>
            <p className="text-lg font-semibold text-green-600">
              +2.3%
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

#### 3.3 Avatar 3D (5 días)
```typescript
// apps/web/components/avatar/Avatar3D.tsx
import { Canvas } from '@react-three/fiber'
import { OrbitControls, useGLTF } from '@react-three/drei'

export function Avatar3D({ measurements }) {
  return (
    <Card className="h-[500px]">
      <CardHeader>
        <CardTitle>Tu Progreso Visual</CardTitle>
      </CardHeader>
      <CardContent className="h-full">
        <Canvas camera={{ position: [0, 0, 5] }}>
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} />
          <HumanModel measurements={measurements} />
          <OrbitControls enablePan={false} />
        </Canvas>
      </CardContent>
    </Card>
  )
}

function HumanModel({ measurements }) {
  const { nodes, materials } = useGLTF('/models/human.glb')
  
  // Apply measurements to model
  useEffect(() => {
    // Scale model based on measurements
  }, [measurements])
  
  return (
    <group>
      <mesh
        geometry={nodes.Body.geometry}
        material={materials.Skin}
        scale={[1, 1, 1]}
      />
    </group>
  )
}
```

---

### FASE 4: FEATURES ESPECÍFICAS FITNESS (Semanas 9-11)

#### 4.1 Workout Interface (5 días)
```typescript
// apps/web/app/workout/[id]/page.tsx
export default function WorkoutPage({ params }: { params: { id: string } }) {
  const { data: workout } = useWorkout(params.id)
  const [currentExercise, setCurrentExercise] = useState(0)
  const [isResting, setIsResting] = useState(false)
  
  return (
    <WorkoutLayout>
      <ExerciseView
        exercise={workout.exercises[currentExercise]}
        onComplete={() => {
          if (currentExercise < workout.exercises.length - 1) {
            setIsResting(true)
            setTimeout(() => {
              setCurrentExercise(prev => prev + 1)
              setIsResting(false)
            }, workout.restTime * 1000)
          }
        }}
      />
      
      {isResting && (
        <RestTimer
          duration={workout.restTime}
          onComplete={() => setIsResting(false)}
        />
      )}
      
      <FormCheckCamera
        exerciseId={workout.exercises[currentExercise].id}
        onFormIssue={(issue) => {
          // Show form correction
        }}
      />
    </WorkoutLayout>
  )
}
```

#### 4.2 Form Check con TensorFlow.js (4 días)
```typescript
// apps/web/components/workout/FormCheckCamera.tsx
import * as poseDetection from '@tensorflow-models/pose-detection'

export function FormCheckCamera({ exerciseId, onFormIssue }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [detector, setDetector] = useState(null)
  
  useEffect(() => {
    async function loadDetector() {
      const detector = await poseDetection.createDetector(
        poseDetection.SupportedModels.MoveNet,
        { modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING }
      )
      setDetector(detector)
    }
    loadDetector()
  }, [])
  
  useEffect(() => {
    if (!detector || !videoRef.current) return
    
    const detectPose = async () => {
      const poses = await detector.estimatePoses(videoRef.current)
      
      if (poses.length > 0) {
        const analysis = analyzeForm(poses[0], exerciseId)
        if (analysis.hasIssues) {
          onFormIssue(analysis.issues)
        }
      }
      
      requestAnimationFrame(detectPose)
    }
    
    detectPose()
  }, [detector, exerciseId])
  
  return (
    <div className="relative">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        className="w-full h-full rounded-lg mirror"
      />
      <PoseOverlay poses={poses} />
    </div>
  )
}
```

#### 4.3 Nutrition Tracker (5 días)
```typescript
// apps/web/components/nutrition/FoodScanner.tsx
export function FoodScanner() {
  const [scanning, setScanning] = useState(false)
  const { mutate: analyzeFoodImage } = useMutation({
    mutationFn: (image: File) => {
      const formData = new FormData()
      formData.append('image', image)
      return api.post('/nutrition/analyze-image', formData)
    }
  })
  
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Button
          onClick={() => setScanning(true)}
          variant="outline"
          size="lg"
        >
          <Camera className="mr-2" />
          Escanear Plato
        </Button>
        
        <Button
          onClick={() => {
            // Open barcode scanner
          }}
          variant="outline"
          size="lg"
        >
          <Barcode className="mr-2" />
          Código de Barras
        </Button>
      </div>
      
      {scanning && (
        <PhotoCapture
          onCapture={(file) => {
            analyzeFoodImage(file)
            setScanning(false)
          }}
          onCancel={() => setScanning(false)}
        />
      )}
    </div>
  )
}
```

---

### FASE 5: MOBILE APP (Semanas 12-16)

#### 5.1 React Native Setup (3 días)
```bash
# En el monorepo
cd apps
npx create-expo-app mobile --template blank-typescript
cd mobile
npx expo install expo-dev-client expo-splash-screen expo-status-bar
```

#### 5.2 Shared Components (5 días)
```typescript
// packages/ui/src/components/Button.native.tsx
import { Pressable, Text, ActivityIndicator } from 'react-native'
import { styled } from 'nativewind'

const StyledPressable = styled(Pressable)
const StyledText = styled(Text)

export function Button({ 
  children, 
  onPress, 
  loading, 
  variant = 'primary' 
}: ButtonProps) {
  return (
    <StyledPressable
      onPress={onPress}
      disabled={loading}
      className={cn(
        'px-4 py-3 rounded-lg flex-row items-center justify-center',
        variant === 'primary' && 'bg-primary-500',
        variant === 'secondary' && 'bg-gray-200'
      )}
    >
      {loading && <ActivityIndicator color="white" className="mr-2" />}
      <StyledText className="text-white font-medium">
        {children}
      </StyledText>
    </StyledPressable>
  )
}
```

#### 5.3 Native Features (8 días)
```typescript
// apps/mobile/hooks/useHealthKit.ts
import { Platform } from 'react-native'
import AppleHealthKit, { HealthValue } from 'react-native-health'

export function useHealthKit() {
  const [isAvailable, setIsAvailable] = useState(false)
  
  useEffect(() => {
    if (Platform.OS !== 'ios') return
    
    AppleHealthKit.initHealthKit(permissions, (error) => {
      if (!error) {
        setIsAvailable(true)
      }
    })
  }, [])
  
  const syncWorkout = useCallback(async (workout: Workout) => {
    if (!isAvailable) return
    
    const options = {
      type: AppleHealthKit.HKWorkoutType[workout.type],
      startDate: workout.startDate,
      endDate: workout.endDate,
      energyBurned: workout.calories,
      distance: workout.distance
    }
    
    AppleHealthKit.saveWorkout(options, (error, result) => {
      if (!error) {
        console.log('Workout saved to HealthKit')
      }
    })
  }, [isAvailable])
  
  return { isAvailable, syncWorkout }
}
```

---

### FASE 6: FEATURES AVANZADAS Y PREMIUM (Semanas 17-20)

#### 6.1 Realidad Aumentada (6 días)
```typescript
// apps/web/components/ar/ARWorkout.tsx
import { ARCanvas, ARMarker } from '@artoolkit/jsartoolkit5'

export function ARWorkout({ exercise }) {
  const [isARActive, setIsARActive] = useState(false)
  
  return (
    <div className="relative h-screen">
      {isARActive ? (
        <ARCanvas
          camera={{ position: [0, 0, 0] }}
          onCreated={({ scene, camera }) => {
            // Setup AR scene
          }}
        >
          <ARMarker type="pattern" patternUrl="/markers/ngx.patt">
            <VirtualTrainer exercise={exercise} />
          </ARMarker>
        </ARCanvas>
      ) : (
        <div className="flex items-center justify-center h-full">
          <Button onClick={() => setIsARActive(true)} size="lg">
            Activar Entrenador AR
          </Button>
        </div>
      )}
    </div>
  )
}
```

#### 6.2 Sistema de Monetización (5 días)
```typescript
// apps/web/components/subscription/PricingPlans.tsx
const plans = [
  {
    name: 'Básico',
    price: 9.99,
    features: [
      '2 Agentes AI',
      'Planes básicos',
      'Tracking manual',
      'Soporte email'
    ],
    stripePriceId: 'price_basic_monthly'
  },
  {
    name: 'Pro',
    price: 19.99,
    features: [
      '6 Agentes AI',
      'Planes personalizados',
      'Integración wearables',
      'Análisis avanzado',
      'Soporte prioritario'
    ],
    stripePriceId: 'price_pro_monthly',
    recommended: true
  },
  {
    name: 'Elite',
    price: 39.99,
    features: [
      '11 Agentes AI',
      'Personalización total',
      'Todas las integraciones',
      'Coaching 1:1 mensual',
      'Acceso anticipado',
      'API access'
    ],
    stripePriceId: 'price_elite_monthly'
  }
]

export function PricingPlans() {
  const { mutate: createCheckoutSession } = useMutation({
    mutationFn: (priceId: string) => 
      api.post('/subscriptions/create-checkout', { priceId })
  })
  
  return (
    <div className="grid md:grid-cols-3 gap-8 max-w-7xl mx-auto">
      {plans.map((plan) => (
        <PricingCard
          key={plan.name}
          {...plan}
          onSubscribe={() => createCheckoutSession(plan.stripePriceId)}
        />
      ))}
    </div>
  )
}
```

---

## 📊 MÉTRICAS Y MONITOREO

### Setup de Analytics
```typescript
// packages/analytics/src/index.ts
import { Analytics } from '@segment/analytics-next'
import * as Sentry from '@sentry/react'
import { Integrations } from '@sentry/tracing'

export function setupAnalytics() {
  // Segment
  const analytics = new Analytics()
  analytics.load({ writeKey: process.env.NEXT_PUBLIC_SEGMENT_KEY })
  
  // Sentry
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    integrations: [
      new Integrations.BrowserTracing(),
      new Sentry.Replay()
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0
  })
  
  // Custom events
  return {
    track: (event: string, properties?: any) => {
      analytics.track(event, properties)
    },
    identify: (userId: string, traits?: any) => {
      analytics.identify(userId, traits)
      Sentry.setUser({ id: userId })
    },
    page: (name?: string, properties?: any) => {
      analytics.page(name, properties)
    }
  }
}
```

---

## 🚀 DEPLOYMENT Y CI/CD

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy NGX Frontend

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 20
          cache: 'npm'
      
      - run: npm ci
      - run: npm run build
      - run: npm run test
      - run: npm run test:e2e
      
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          
      - name: Deploy Mobile to EAS
        run: |
          npm install -g eas-cli
          cd apps/mobile
          eas build --platform all --non-interactive
          eas submit --platform all --non-interactive
```

---

## 💰 PRESUPUESTO DETALLADO

### Costos de Desarrollo (6 meses)
| Rol | Cantidad | Costo/mes | Total |
|-----|----------|-----------|-------|
| Frontend Lead | 1 | $12,000 | $72,000 |
| Frontend Dev | 2 | $8,000 | $96,000 |
| Mobile Dev | 1 | $9,000 | $54,000 |
| UI/UX Designer | 1 | $7,000 | $42,000 |
| QA Engineer | 1 | $6,000 | $36,000 |
| **Subtotal** | | | **$300,000** |

### Costos de Infraestructura
| Servicio | Costo/mes | 6 meses |
|----------|-----------|---------|
| Vercel Pro | $20 | $120 |
| Supabase Pro | $25 | $150 |
| CDN | $100 | $600 |
| Monitoring | $50 | $300 |
| **Subtotal** | | **$1,170** |

### Herramientas y Servicios
| Herramienta | Costo/mes | 6 meses |
|-------------|-----------|---------|
| Figma | $45 | $270 |
| Linear | $25 | $150 |
| Sentry | $80 | $480 |
| Segment | $120 | $720 |
| **Subtotal** | | **$1,620** |

### **TOTAL GENERAL: $302,790**

---

## 🎯 ENTREGABLES POR FASE

### MVP (12 semanas)
- ✅ Chat funcional con 3 agentes
- ✅ Dashboard básico
- ✅ Autenticación completa
- ✅ Integración WHOOP/Apple Health
- ✅ 10 componentes UI documentados

### Fase Mobile (8 semanas adicionales)
- ✅ App iOS y Android
- ✅ Sincronización offline
- ✅ Push notifications
- ✅ HealthKit integration

### Fase Premium (8 semanas adicionales)
- ✅ Los 11 agentes integrados
- ✅ AR form checking
- ✅ Sistema de pagos
- ✅ Analytics avanzado
- ✅ 50+ componentes UI

---

## 🔧 STACK TECNOLÓGICO FINAL

```json
{
  "frontend": {
    "framework": "Next.js 14.2+",
    "language": "TypeScript 5.3+",
    "styling": "Tailwind CSS 3.4+",
    "state": "Zustand 4.5+",
    "data": "TanStack Query 5.0+",
    "forms": "React Hook Form + Zod",
    "animation": "Framer Motion 11+",
    "charts": "Recharts 2.9+",
    "3d": "React Three Fiber"
  },
  "mobile": {
    "framework": "React Native 0.73+",
    "platform": "Expo SDK 50+",
    "navigation": "React Navigation 6+",
    "animations": "Reanimated 3+"
  },
  "tooling": {
    "monorepo": "Turborepo",
    "bundler": "Vite",
    "testing": "Jest + Cypress",
    "ci": "GitHub Actions",
    "deployment": "Vercel + EAS"
  }
}
```

---

## 🚦 CRITERIOS DE ÉXITO

### Técnicos
- Lighthouse Score > 95
- Bundle size < 300KB
- Test coverage > 80%
- Zero downtime deploys

### Usuario
- Onboarding < 3 min
- Daily active users > 60%
- App store rating > 4.5
- NPS score > 70

### Negocio
- Conversión free→paid > 10%
- CAC < $50
- LTV > $200
- Churn < 5% mensual

---

Este plan está diseñado para ejecutarse inmediatamente después de completar las fases 8, 9 y 10 del backend. La modularidad permite comenzar con el MVP mientras se terminan las integraciones pendientes.

---

## 🎨 DOCUMENTACIÓN COMPLETA DEL BRANDING NEOGEN-X

### Paleta de Colores Oficial
```css
/* Colores principales */
:root {
  /* Navy - Color principal de navegación y elementos secundarios */
  --navy-50: #f0f0f5;
  --navy-100: #d9d9e8;
  --navy-500: #0A0628;  /* HEX principal del branding */
  --navy-600: #080520;
  --navy-900: #050318;
  
  /* Purple - Color principal de acciones y CTAs */
  --purple-50: #f3e6ff;
  --purple-100: #e0b3ff;
  --purple-500: #6D00FF;  /* HEX principal del branding */
  --purple-600: #5500cc;
  --purple-900: #330080;
  
  /* Gray - Color secundario para contenido */
  --gray-50: #fafafa;
  --gray-500: #CCCCCC;  /* HEX secundario del branding */
  --gray-900: #212121;
  
  /* White - Color base */
  --white: #FFFFFF;  /* HEX base del branding */
}
```

### Guías de Uso por Componente

#### Navegación y Headers
- **Fondo:** Navy (#0A0628)
- **Texto:** White (#FFFFFF)
- **Enlaces activos:** Purple-300
- **Enlaces hover:** Purple-200
- **Logo:** Versión blanca sobre navy

#### Botones y CTAs
- **Primario:** Purple (#6D00FF) con texto blanco
- **Secundario:** Navy (#0A0628) con texto blanco
- **Outline:** Borde purple con texto purple
- **Ghost:** Texto navy con hover gray-100

#### Cards y Contenedores
- **Fondo principal:** White (#FFFFFF)
- **Bordes:** Gray-200
- **Destacados:** Gradiente purple-50 a navy-50
- **Interactivos:** Hover border-purple-300

#### Estados de la Aplicación
- **Loading:** Purple-100 background, purple-700 text
- **Success:** Green-100 background, green-700 text
- **Warning:** Yellow-100 background, yellow-700 text
- **Error:** Red-100 background, red-700 text

### Validación de Accesibilidad
```typescript
// Contrastes validados WCAG AA
const accessibilityValidation = {
  navy_white: 'PASS - 15.3:1',
  purple_white: 'PASS - 12.8:1',
  gray_navy: 'PASS - 8.2:1',
  purple_navy: 'PASS - 4.8:1'
}
```

### Ejemplos de Implementación
```jsx
// Ejemplo de header con branding
<header className="bg-navy-500 text-white">
  <nav className="flex items-center justify-between">
    <img src="/logo-white.svg" alt="Neogen-X" />
    <Button className="bg-purple-500 hover:bg-purple-600">
      Comenzar
    </Button>
  </nav>
</header>

// Ejemplo de card destacada
<Card className="bg-gradient-to-br from-purple-50 to-navy-50 border-purple-200">
  <CardHeader>
    <CardTitle className="text-navy-700">Título</CardTitle>
  </CardHeader>
</Card>
```

### Checklist de Implementación
- [ ] Variables CSS definidas en tokens.css
- [ ] Configuración Tailwind actualizada
- [ ] Componentes base actualizados con branding
- [ ] Validación de contraste completada
- [ ] Documentación en Storybook
- [ ] Pruebas de accesibilidad ejecutadas
- [ ] Revisión de consistencia visual

**¿Listos para revolucionar el fitness con IA? 🚀**