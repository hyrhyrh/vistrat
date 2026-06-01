export interface PromptTemplate {
  id: string
  name: string
  category: string
  priority: string
  system_prompt: string
  user_prompt: string
  description: string
  variables: PromptVariable[]
  detection_criteria: DetectionCriteria
  is_active: boolean
  is_system_template: boolean
  usage_count: number
  success_rate: number
  created_at: string
  tags: string[]
}

export interface PromptVariable {
  name: string
  type: string
  description: string
  default_value?: any
  required: boolean
}

export interface DetectionCriteria {
  confidence_threshold: number
  detection_keywords: string[]
  exclusion_keywords: string[]
  enable_annotation: boolean
}