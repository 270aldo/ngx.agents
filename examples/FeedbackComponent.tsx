import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, Star, MessageSquare, AlertCircle, Lightbulb } from 'lucide-react';

interface FeedbackComponentProps {
  conversationId: string;
  messageId: string;
  authToken: string;
  apiUrl?: string;
  onFeedbackSubmitted?: (feedbackId: string) => void;
}

type FeedbackType = 'thumbs_up' | 'thumbs_down' | 'rating' | 'comment' | 'issue' | 'suggestion';
type FeedbackCategory = 'accuracy' | 'relevance' | 'completeness' | 'speed' | 'helpfulness' | 'user_experience' | 'technical_issue' | 'other';

const FeedbackComponent: React.FC<FeedbackComponentProps> = ({
  conversationId,
  messageId,
  authToken,
  apiUrl = 'http://localhost:8000',
  onFeedbackSubmitted
}) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackType, setFeedbackType] = useState<FeedbackType | null>(null);
  const [rating, setRating] = useState<number>(0);
  const [comment, setComment] = useState('');
  const [categories, setCategories] = useState<FeedbackCategory[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const categoryOptions: { value: FeedbackCategory; label: string }[] = [
    { value: 'accuracy', label: 'Precisión' },
    { value: 'relevance', label: 'Relevancia' },
    { value: 'completeness', label: 'Completitud' },
    { value: 'speed', label: 'Velocidad' },
    { value: 'helpfulness', label: 'Utilidad' },
    { value: 'user_experience', label: 'Experiencia de Usuario' },
    { value: 'technical_issue', label: 'Problema Técnico' },
    { value: 'other', label: 'Otro' }
  ];

  const handleQuickFeedback = async (type: 'thumbs_up' | 'thumbs_down') => {
    setFeedbackType(type);
    await submitFeedback(type);
  };

  const submitFeedback = async (type: FeedbackType = feedbackType!) => {
    if (!type) return;

    setIsSubmitting(true);

    try {
      const payload = {
        conversation_id: conversationId,
        message_id: messageId,
        feedback_type: type,
        rating: type === 'rating' ? rating : undefined,
        comment: comment || undefined,
        categories: categories.length > 0 ? categories : undefined,
        metadata: {
          client: 'react-feedback-component',
          timestamp: new Date().toISOString()
        }
      };

      const response = await fetch(`${apiUrl}/feedback/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      setSubmitted(true);
      setShowFeedback(false);
      
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted(result.feedback_id);
      }

      // Reset después de 3 segundos
      setTimeout(() => {
        setSubmitted(false);
        setFeedbackType(null);
        setRating(0);
        setComment('');
        setCategories([]);
      }, 3000);

    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Error al enviar feedback. Por favor intenta de nuevo.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleCategory = (category: FeedbackCategory) => {
    setCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  if (submitted) {
    return (
      <div className="feedback-submitted">
        <span className="success-icon">✓</span>
        <span>¡Gracias por tu feedback!</span>
      </div>
    );
  }

  return (
    <div className="feedback-component">
      <div className="feedback-actions">
        {/* Botones rápidos */}
        <button
          className={`feedback-btn ${feedbackType === 'thumbs_up' ? 'active' : ''}`}
          onClick={() => handleQuickFeedback('thumbs_up')}
          disabled={isSubmitting}
          title="Me gusta"
        >
          <ThumbsUp size={16} />
        </button>
        
        <button
          className={`feedback-btn ${feedbackType === 'thumbs_down' ? 'active' : ''}`}
          onClick={() => handleQuickFeedback('thumbs_down')}
          disabled={isSubmitting}
          title="No me gusta"
        >
          <ThumbsDown size={16} />
        </button>

        {/* Botón para más opciones */}
        <button
          className="feedback-btn"
          onClick={() => setShowFeedback(!showFeedback)}
          disabled={isSubmitting}
          title="Más opciones de feedback"
        >
          <MessageSquare size={16} />
        </button>
      </div>

      {/* Panel expandido de feedback */}
      {showFeedback && (
        <div className="feedback-panel">
          <h4>Danos tu feedback</h4>
          
          {/* Tipo de feedback */}
          <div className="feedback-types">
            <button
              className={`type-btn ${feedbackType === 'rating' ? 'active' : ''}`}
              onClick={() => setFeedbackType('rating')}
            >
              <Star size={16} /> Calificar
            </button>
            <button
              className={`type-btn ${feedbackType === 'comment' ? 'active' : ''}`}
              onClick={() => setFeedbackType('comment')}
            >
              <MessageSquare size={16} /> Comentar
            </button>
            <button
              className={`type-btn ${feedbackType === 'issue' ? 'active' : ''}`}
              onClick={() => setFeedbackType('issue')}
            >
              <AlertCircle size={16} /> Reportar problema
            </button>
            <button
              className={`type-btn ${feedbackType === 'suggestion' ? 'active' : ''}`}
              onClick={() => setFeedbackType('suggestion')}
            >
              <Lightbulb size={16} /> Sugerir mejora
            </button>
          </div>

          {/* Rating */}
          {feedbackType === 'rating' && (
            <div className="rating-section">
              <p>Califica esta respuesta:</p>
              <div className="stars">
                {[1, 2, 3, 4, 5].map(star => (
                  <button
                    key={star}
                    className={`star ${rating >= star ? 'filled' : ''}`}
                    onClick={() => setRating(star)}
                  >
                    <Star size={20} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Comentario */}
          {['comment', 'issue', 'suggestion'].includes(feedbackType!) && (
            <div className="comment-section">
              <textarea
                placeholder={
                  feedbackType === 'issue' 
                    ? 'Describe el problema...'
                    : feedbackType === 'suggestion'
                    ? 'Comparte tu sugerencia...'
                    : 'Escribe tu comentario...'
                }
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
              />
            </div>
          )}

          {/* Categorías */}
          <div className="categories-section">
            <p>Categorías relacionadas (opcional):</p>
            <div className="categories">
              {categoryOptions.map(cat => (
                <button
                  key={cat.value}
                  className={`category-tag ${categories.includes(cat.value) ? 'active' : ''}`}
                  onClick={() => toggleCategory(cat.value)}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Botones de acción */}
          <div className="feedback-actions-panel">
            <button
              className="btn-cancel"
              onClick={() => setShowFeedback(false)}
            >
              Cancelar
            </button>
            <button
              className="btn-submit"
              onClick={() => submitFeedback()}
              disabled={
                isSubmitting || 
                !feedbackType || 
                (feedbackType === 'rating' && rating === 0) ||
                (['comment', 'issue', 'suggestion'].includes(feedbackType) && !comment.trim())
              }
            >
              {isSubmitting ? 'Enviando...' : 'Enviar Feedback'}
            </button>
          </div>
        </div>
      )}

      <style jsx>{`
        .feedback-component {
          position: relative;
          margin-top: 0.5rem;
        }

        .feedback-actions {
          display: flex;
          gap: 0.5rem;
        }

        .feedback-btn {
          padding: 0.25rem 0.5rem;
          border: 1px solid #e0e0e0;
          background: white;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.2s;
          color: #666;
        }

        .feedback-btn:hover {
          background: #f5f5f5;
          border-color: #ccc;
        }

        .feedback-btn.active {
          background: #007bff;
          color: white;
          border-color: #007bff;
        }

        .feedback-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .feedback-submitted {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: #28a745;
          font-size: 0.875rem;
          padding: 0.5rem;
        }

        .success-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 20px;
          height: 20px;
          background: #28a745;
          color: white;
          border-radius: 50%;
          font-size: 0.75rem;
        }

        .feedback-panel {
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          margin-top: 0.5rem;
          padding: 1rem;
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          z-index: 10;
        }

        .feedback-panel h4 {
          margin: 0 0 1rem 0;
          font-size: 1rem;
          color: #333;
        }

        .feedback-types {
          display: flex;
          gap: 0.5rem;
          margin-bottom: 1rem;
          flex-wrap: wrap;
        }

        .type-btn {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          padding: 0.375rem 0.75rem;
          border: 1px solid #e0e0e0;
          background: white;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.875rem;
          transition: all 0.2s;
        }

        .type-btn:hover {
          background: #f5f5f5;
        }

        .type-btn.active {
          background: #007bff;
          color: white;
          border-color: #007bff;
        }

        .rating-section p,
        .categories-section p {
          margin: 0 0 0.5rem 0;
          font-size: 0.875rem;
          color: #666;
        }

        .stars {
          display: flex;
          gap: 0.25rem;
          margin-bottom: 1rem;
        }

        .star {
          padding: 0.25rem;
          border: none;
          background: none;
          cursor: pointer;
          color: #ddd;
          transition: color 0.2s;
        }

        .star:hover,
        .star.filled {
          color: #ffc107;
        }

        .comment-section {
          margin-bottom: 1rem;
        }

        .comment-section textarea {
          width: 100%;
          padding: 0.5rem;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          font-size: 0.875rem;
          resize: vertical;
        }

        .categories {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1rem;
        }

        .category-tag {
          padding: 0.25rem 0.75rem;
          border: 1px solid #e0e0e0;
          background: white;
          border-radius: 16px;
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.2s;
        }

        .category-tag:hover {
          background: #f5f5f5;
        }

        .category-tag.active {
          background: #e3f2fd;
          border-color: #2196f3;
          color: #1976d2;
        }

        .feedback-actions-panel {
          display: flex;
          gap: 0.5rem;
          justify-content: flex-end;
        }

        .btn-cancel,
        .btn-submit {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 4px;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-cancel {
          background: #f5f5f5;
          color: #666;
        }

        .btn-cancel:hover {
          background: #e0e0e0;
        }

        .btn-submit {
          background: #007bff;
          color: white;
        }

        .btn-submit:hover {
          background: #0056b3;
        }

        .btn-submit:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

export default FeedbackComponent;