# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  resource_suffix = random_string.suffix.result
  common_tags = merge(var.tags, {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  })
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}-${local.resource_suffix}"
  location = var.location
  tags     = local.common_tags
}

# Azure Cosmos DB Account with Gremlin API
resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-${var.project_name}-${var.environment}-${local.resource_suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  capabilities {
    name = "EnableGremlin"
  }

  consistency_policy {
    consistency_level = var.cosmos_consistency_level
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }

  tags = local.common_tags
}

# Cosmos DB Gremlin Database
resource "azurerm_cosmosdb_gremlin_database" "main" {
  name                = "${var.project_name}-graph-db"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  throughput          = var.cosmos_throughput
}

# Azure Event Hub Namespace
resource "azurerm_eventhub_namespace" "main" {
  name                = "evhns-${var.project_name}-${var.environment}-${local.resource_suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.eventhub_sku
  capacity            = var.eventhub_capacity

  tags = local.common_tags
}

# Azure Event Hub
resource "azurerm_eventhub" "main" {
  name                = "evh-${var.project_name}-${var.environment}"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = var.eventhub_partition_count
  message_retention   = var.eventhub_message_retention
}

# Event Hub Data Owner Role Assignment for deploying user
resource "azurerm_role_assignment" "eventhub_deployer" {
  scope                = azurerm_eventhub_namespace.main.id
  role_definition_name = "Azure Event Hubs Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Cosmos DB Gremlin Graph
resource "azurerm_cosmosdb_gremlin_graph" "user_products" {
  name                = "user_products"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_gremlin_database.main.name
  partition_key_path  = "/partitionKey"

  index_policy {
    automatic      = true
    indexing_mode  = "consistent"
    included_paths = ["/*"]
    excluded_paths = ["/\"_etag\"/?"]
  }
}

# Get current client configuration for role assignment
data "azurerm_client_config" "current" {}

# Cosmos DB SQL Role Assignment for deploying user
resource "azurerm_cosmosdb_sql_role_assignment" "deployer" {
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = "${azurerm_cosmosdb_account.main.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = data.azurerm_client_config.current.object_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Azure AI Foundry Account
resource "azurerm_cognitive_account" "ai_foundry" {
  name                = "aifoundry-${var.project_name}-${local.resource_suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "AIServices"
  sku_name            = var.openai_sku

  identity {
    type = "SystemAssigned"
  }

  # required for stateful development in Foundry including agent service
  custom_subdomain_name      = "aifoundry-${var.project_name}-${local.resource_suffix}"
  project_management_enabled = true

  tags = local.common_tags
}

# GPT Model Deployment in AI Foundry
resource "azurerm_cognitive_deployment" "gpt" {
  depends_on = [
    azurerm_cognitive_account.ai_foundry
  ]

  name                 = var.openai_model_name
  cognitive_account_id = azurerm_cognitive_account.ai_foundry.id

  sku {
    name     = "GlobalStandard"
    capacity = var.openai_deployment_capacity
  }

  model {
    format  = "OpenAI"
    name    = var.openai_model_name
    version = var.openai_model_version
  }
}

resource "azapi_resource" "ai_foundry_project" {
  type                      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name                      = "project-${var.project_name}-${local.resource_suffix}"
  parent_id                 = azurerm_cognitive_account.ai_foundry.id
  location                  = var.location
  schema_validation_enabled = false
  response_export_values    = ["*"]

  body = {
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }

    properties = {
      displayName = "project"
      description = "Graph Chat Project"
    }
  }
}

# Cognitive Services OpenAI Contributor Role Assignment for deploying user
resource "azurerm_role_assignment" "openai_deployer" {
  scope                = azurerm_cognitive_account.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}
