import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Rutas públicas que no requieren autenticación
const publicRoutes = [
  '/',
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
  '/about',
  '/terms',
  '/privacy',
]

// Rutas de autenticación que redirigen si ya estás autenticado
const authRoutes = ['/login', '/register', '/forgot-password']

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname
  const isPublicRoute = publicRoutes.includes(path)
  const isAuthRoute = authRoutes.includes(path)
  
  // Por ahora, solo verificamos si existe un token
  // En producción, deberías verificar el token con Supabase
  const token = request.cookies.get('sb-access-token')?.value
  
  // Redirigir al dashboard si intentas acceder a rutas de auth estando autenticado
  if (isAuthRoute && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }
  
  // Redirigir al login si intentas acceder a rutas privadas sin autenticación
  if (!isPublicRoute && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)' 
  ],
}