# Resource Group Outputs
output "resource_group_name" {
  description = "The name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "The location of the resource group"
  value       = azurerm_resource_group.main.location
}

# Cosmos DB Outputs
output "cosmosdb_account_name" {
  description = "The name of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.name
}

output "cosmosdb_account_endpoint" {
  description = "The endpoint of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "cosmosdb_gremlin_endpoint" {
  description = "The Gremlin endpoint of the Cosmos DB account"
  value       = "wss://${azurerm_cosmosdb_account.main.name}.gremlin.cosmos.azure.com:443/"
}

output "cosmosdb_primary_key" {
  description = "The primary key for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.primary_key
  sensitive   = true
}

output "cosmosdb_database_name" {
  description = "The name of the Cosmos DB Gremlin database"
  value       = azurerm_cosmosdb_gremlin_database.main.name
}

# Event Hub Outputs
output "eventhub_namespace_name" {
  description = "The name of the Event Hub namespace"
  value       = azurerm_eventhub_namespace.main.name
}

output "eventhub_name" {
  description = "The name of the Event Hub"
  value       = azurerm_eventhub.main.name
}

output "eventhub_namespace_connection_string" {
  description = "The primary connection string for the Event Hub namespace"
  value       = azurerm_eventhub_namespace.main.default_primary_connection_string
  sensitive   = true
}

# Cosmos DB Graph Outputs
output "cosmosdb_graph_name" {
  description = "The name of the Cosmos DB Gremlin graph"
  value       = azurerm_cosmosdb_gremlin_graph.user_products.name
}

# Azure AI Foundry Outputs
output "ai_foundry_name" {
  description = "The name of the AI Foundry account"
  value       = azurerm_cognitive_account.ai_foundry.name
}

output "azure_ai_project_endpoint" {
  description = "The endpoint for the AI Foundry account"
  value       = azapi_resource.ai_foundry_project.output.properties.endpoints["AI Foundry API"]
}

output "azure_openai_endpoint" {
  value = "https://${azurerm_cognitive_account.ai_foundry.name}.openai.azure.com/"
}

output "azure_openai_chat_deployment_name" {
  description = "The name of the OpenAI deployment"
  value       = azurerm_cognitive_deployment.gpt.name
}

output "azure_ai_model_deployment_name" {
  description = "The name of the OpenAI deployment"
  value       = azurerm_cognitive_deployment.gpt.name
}
