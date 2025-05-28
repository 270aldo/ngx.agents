// Demo data for testing progress components
export const demoProgressData = [
  {
    id: '1',
    user_id: 'demo-user',
    date: '2024-10-01',
    weight: 85.5,
    body_fat_percentage: 22.5,
    measurements: {
      chest: 102,
      waist: 90,
      hips: 98,
      biceps: 35,
      thighs: 58
    },
    photos: [
      {
        id: '1',
        url: 'https://via.placeholder.com/400x600',
        type: 'front' as const,
        created_at: '2024-10-01'
      }
    ]
  },
  {
    id: '2',
    user_id: 'demo-user',
    date: '2024-11-01',
    weight: 83.2,
    body_fat_percentage: 20.8,
    measurements: {
      chest: 103,
      waist: 87,
      hips: 97,
      biceps: 36,
      thighs: 59
    },
    photos: [
      {
        id: '2',
        url: 'https://via.placeholder.com/400x600',
        type: 'front' as const,
        created_at: '2024-11-01'
      }
    ]
  },
  {
    id: '3',
    user_id: 'demo-user',
    date: '2024-12-01',
    weight: 81.5,
    body_fat_percentage: 19.2,
    measurements: {
      chest: 104,
      waist: 85,
      hips: 96,
      biceps: 37,
      thighs: 60
    },
    photos: [
      {
        id: '3',
        url: 'https://via.placeholder.com/400x600',
        type: 'front' as const,
        created_at: '2024-12-01'
      }
    ]
  },
  {
    id: '4',
    user_id: 'demo-user',
    date: '2025-01-01',
    weight: 80.0,
    body_fat_percentage: 18.0,
    measurements: {
      chest: 105,
      waist: 83,
      hips: 95,
      biceps: 38,
      thighs: 61
    },
    photos: [
      {
        id: '4',
        url: 'https://via.placeholder.com/400x600',
        type: 'front' as const,
        created_at: '2025-01-01'
      }
    ]
  }
]

export const demoGoals = [
  {
    id: '1',
    title: 'Perder 10kg en 6 meses',
    target_value: 75,
    current_value: 80,
    unit: 'kg',
    target_date: '2025-04-01',
    created_at: '2024-10-01',
    status: 'active' as const,
    category: 'weight' as const
  },
  {
    id: '2',
    title: 'Reducir grasa corporal al 15%',
    target_value: 15,
    current_value: 18,
    unit: '%',
    target_date: '2025-06-01',
    created_at: '2024-10-01',
    status: 'active' as const,
    category: 'body_fat' as const
  },
  {
    id: '3',
    title: 'Aumentar masa muscular',
    target_value: 42,
    current_value: 38,
    unit: 'kg',
    target_date: '2025-05-01',
    created_at: '2024-11-01',
    status: 'active' as const,
    category: 'muscle' as const
  }
]

export const demoAchievements = [
  {
    id: '1',
    title: 'Primera Semana Completa',
    description: 'Completaste tu primera semana de entrenamiento',
    icon: 'trophy',
    category: 'Inicio',
    unlocked_at: '2024-10-07',
    rarity: 'common' as const
  },
  {
    id: '2',
    title: 'Racha de 30 Días',
    description: 'Mantuviste una racha de entrenamiento por 30 días',
    icon: 'flame',
    category: 'Consistencia',
    unlocked_at: '2024-11-01',
    rarity: 'rare' as const
  },
  {
    id: '3',
    title: 'Meta de Peso Alcanzada',
    description: 'Alcanzaste tu primera meta de peso',
    icon: 'target',
    category: 'Metas',
    unlocked_at: undefined,
    progress: 80,
    rarity: 'epic' as const
  },
  {
    id: '4',
    title: 'Transformación Completa',
    description: 'Completaste tu transformación física',
    icon: 'star',
    category: 'Elite',
    unlocked_at: undefined,
    progress: 40,
    rarity: 'legendary' as const
  }
]

export const demoMilestones = [
  {
    id: '1',
    title: 'Primer Mes Completado',
    description: 'Has completado tu primer mes de entrenamiento constante',
    date: '2024-11-01',
    type: 'habit' as const,
    celebrated: true
  },
  {
    id: '2',
    title: '5kg Perdidos',
    description: '¡Felicitaciones! Has perdido tus primeros 5kg',
    date: '2025-01-01',
    type: 'weight' as const,
    value: 5,
    unit: 'kg',
    celebrated: false
  }
]

export const demoStats = {
  total_weight_lost: 5.5,
  total_muscle_gained: 2.5,
  body_fat_change: -4.5,
  streak_days: 45,
  total_workouts: 52,
  total_achievements: 2,
  best_streak: 45,
  start_date: '2024-10-01'
}