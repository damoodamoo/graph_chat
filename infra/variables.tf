variable "subscription_id" {
  description = "The Azure subscription ID"
  type        = string
}

variable "project_name" {
  description = "The name of the project, used as a prefix for all resources"
  type        = string
  default     = "graphchat"
}

variable "environment" {
  description = "The environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "The Azure region where resources will be created"
  type        = string
  default     = "eastus"
}

variable "cosmos_consistency_level" {
  description = "The consistency level for Cosmos DB"
  type        = string
  default     = "Session"
}

variable "cosmos_throughput" {
  description = "The throughput for the Cosmos DB Gremlin database"
  type        = number
  default     = 400
}

variable "eventhub_sku" {
  description = "The SKU for Event Hub namespace"
  type        = string
  default     = "Standard"
}

variable "eventhub_capacity" {
  description = "The capacity (throughput units) for Event Hub namespace"
  type        = number
  default     = 1
}

variable "eventhub_partition_count" {
  description = "The number of partitions for the Event Hub"
  type        = number
  default     = 2
}

variable "eventhub_message_retention" {
  description = "The message retention in days for the Event Hub"
  type        = number
  default     = 1
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "openai_sku" {
  description = "The SKU for Azure OpenAI service"
  type        = string
  default     = "S0"
}

variable "openai_model_name" {
  description = "The name of the OpenAI model to deploy"
  type        = string
  default     = "gpt-4.1"
}

variable "openai_model_version" {
  description = "The version of the OpenAI model to deploy"
  type        = string
  default     = "2024-08-06"
}

variable "openai_deployment_capacity" {
  description = "The capacity (tokens per minute in thousands) for the OpenAI deployment"
  type        = number
  default     = 10
}
