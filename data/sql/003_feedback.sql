-- Migración para crear las tablas del sistema de feedback
-- Fecha: 2025-05-24

-- Tabla principal de feedback de mensajes
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    conversation_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255),
    feedback_type VARCHAR(50) NOT NULL CHECK (
        feedback_type IN ('thumbs_up', 'thumbs_down', 'rating', 'comment', 'issue', 'suggestion')
    ),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    categories JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para la tabla feedback
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_conversation_id ON feedback(conversation_id);
CREATE INDEX IF NOT EXISTS idx_feedback_message_id ON feedback(message_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_categories ON feedback USING GIN(categories);

-- Tabla de feedback de sesiones completas
CREATE TABLE IF NOT EXISTS session_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    conversation_id VARCHAR(255) NOT NULL UNIQUE, -- Una sesión por conversación
    overall_rating INTEGER NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
    categories_feedback JSONB DEFAULT '{}'::jsonb,
    would_recommend BOOLEAN,
    comment TEXT,
    improvement_suggestions JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para session_feedback
CREATE INDEX IF NOT EXISTS idx_session_feedback_user_id ON session_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_session_feedback_conversation ON session_feedback(conversation_id);
CREATE INDEX IF NOT EXISTS idx_session_feedback_rating ON session_feedback(overall_rating);
CREATE INDEX IF NOT EXISTS idx_session_feedback_recommend ON session_feedback(would_recommend);
CREATE INDEX IF NOT EXISTS idx_session_feedback_created_at ON session_feedback(created_at DESC);

-- Tabla de analytics agregados (para caché y rendimiento)
CREATE TABLE IF NOT EXISTS feedback_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    analytics_type VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'monthly'
    analytics_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(period_start, period_end, analytics_type)
);

-- Índices para feedback_analytics
CREATE INDEX IF NOT EXISTS idx_analytics_period ON feedback_analytics(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_analytics_type ON feedback_analytics(analytics_type);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_feedback_updated_at BEFORE UPDATE
    ON feedback FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Vista para estadísticas rápidas
CREATE OR REPLACE VIEW feedback_stats_view AS
SELECT 
    COUNT(*) as total_feedbacks,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT conversation_id) as unique_conversations,
    AVG(CASE WHEN rating IS NOT NULL THEN rating END) as avg_rating,
    SUM(CASE WHEN feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as thumbs_up_count,
    SUM(CASE WHEN feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as thumbs_down_count,
    SUM(CASE WHEN feedback_type = 'issue' THEN 1 ELSE 0 END) as issues_count,
    CAST(SUM(CASE WHEN feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) AS FLOAT) / 
        NULLIF(SUM(CASE WHEN feedback_type IN ('thumbs_up', 'thumbs_down') THEN 1 ELSE 0 END), 0) as satisfaction_rate
FROM feedback;

-- Vista para NPS (Net Promoter Score)
CREATE OR REPLACE VIEW nps_view AS
WITH nps_calc AS (
    SELECT
        CASE 
            WHEN overall_rating = 5 AND would_recommend = true THEN 'promoter'
            WHEN overall_rating >= 4 THEN 'passive'
            ELSE 'detractor'
        END as nps_category
    FROM session_feedback
    WHERE would_recommend IS NOT NULL
)
SELECT 
    COUNT(*) FILTER (WHERE nps_category = 'promoter') as promoters,
    COUNT(*) FILTER (WHERE nps_category = 'passive') as passives,
    COUNT(*) FILTER (WHERE nps_category = 'detractor') as detractors,
    COUNT(*) as total,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ((COUNT(*) FILTER (WHERE nps_category = 'promoter')::FLOAT - 
              COUNT(*) FILTER (WHERE nps_category = 'detractor')::FLOAT) / 
              COUNT(*)::FLOAT) * 100
        ELSE 0
    END as nps_score
FROM nps_calc;

-- Función para limpiar feedback antiguo (GDPR compliance)
CREATE OR REPLACE FUNCTION cleanup_old_feedback(days_to_keep INTEGER DEFAULT 365)
RETURNS TABLE(deleted_feedback INTEGER, deleted_sessions INTEGER) AS $$
DECLARE
    feedback_count INTEGER;
    session_count INTEGER;
BEGIN
    -- Eliminar feedback antiguo
    WITH deleted AS (
        DELETE FROM feedback 
        WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep
        RETURNING 1
    )
    SELECT COUNT(*) INTO feedback_count FROM deleted;
    
    -- Eliminar sesiones antiguas
    WITH deleted AS (
        DELETE FROM session_feedback 
        WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep
        RETURNING 1
    )
    SELECT COUNT(*) INTO session_count FROM deleted;
    
    RETURN QUERY SELECT feedback_count, session_count;
END;
$$ LANGUAGE plpgsql;

-- Comentarios de documentación
COMMENT ON TABLE feedback IS 'Almacena feedback individual sobre mensajes de los agentes';
COMMENT ON TABLE session_feedback IS 'Almacena feedback sobre sesiones completas de conversación';
COMMENT ON TABLE feedback_analytics IS 'Caché de analytics agregados para mejorar rendimiento';
COMMENT ON COLUMN feedback.feedback_type IS 'Tipo de feedback: thumbs_up, thumbs_down, rating, comment, issue, suggestion';
COMMENT ON COLUMN feedback.categories IS 'Array JSON de categorías: accuracy, relevance, completeness, speed, helpfulness, user_experience, technical_issue, other';
COMMENT ON COLUMN session_feedback.would_recommend IS 'Indicador para calcular Net Promoter Score (NPS)';