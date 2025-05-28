import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface ChatSuggestionsProps {
  onSelect: (suggestion: string) => void
}

const suggestions = [
  {
    category: 'Training',
    icon: '💪',
    questions: [
      'Create a personalized workout plan for muscle gain',
      'What exercises can I do at home without equipment?',
      'How can I improve my running endurance?',
    ],
  },
  {
    category: 'Nutrition',
    icon: '🥗',
    questions: [
      'Design a meal plan for weight loss',
      'What should I eat before and after workouts?',
      'How much protein do I need daily?',
    ],
  },
  {
    category: 'Health',
    icon: '❤️',
    questions: [
      'Analyze my sleep patterns and suggest improvements',
      "What's my current recovery status?",
      'How can I reduce stress through exercise?',
    ],
  },
  {
    category: 'Progress',
    icon: '📈',
    questions: [
      'Show me my fitness progress this month',
      'Am I on track to reach my goals?',
      'What areas need more focus?',
    ],
  },
]

export function ChatSuggestions({ onSelect }: ChatSuggestionsProps) {
  return (
    <div className="space-y-6 py-8">
      <div className="text-center">
        <Sparkles className="h-8 w-8 text-primary mx-auto mb-3" />
        <h3 className="text-xl font-semibold mb-2">How can I help you today?</h3>
        <p className="text-sm text-gray-500">Choose a topic or type your own question</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {suggestions.map((category, categoryIndex) => (
          <motion.div
            key={category.category}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: categoryIndex * 0.1 }}
            className="space-y-3"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{category.icon}</span>
              <h4 className="font-medium text-lg">{category.category}</h4>
            </div>
            <div className="space-y-2">
              {category.questions.map((question, index) => (
                <motion.div
                  key={index}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left text-sm h-auto py-3 px-4 hover:bg-primary/5 hover:border-primary/50"
                    onClick={() => onSelect(question)}
                  >
                    {question}
                  </Button>
                </motion.div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}