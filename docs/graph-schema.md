# Graph Schema Documentation

This document describes the structure of the Azure Cosmos DB Gremlin graph used in the Graph Chat application.

## Overview

The graph models a retail e-commerce domain with customers, articles, products, and their relationships. Articles are specific variations (e.g., size, colour) of products. It enables queries about customer purchase history, product categorization, and behavioral patterns.

## Node Types (Vertices)

### User (`user`)
Represents a customer in the system.

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique customer identifier (hash) |
| `name` | string | Customer identifier (same as id) |
| `age` | int | Customer's age |
| `club_member_status` | string | Membership status (e.g., `ACTIVE`, `PRE-CREATE`) |
| `fashion_news_frequency` | string | Newsletter preference (e.g., `NONE`, `Regularly`) |
| `partitionKey` | string | Partition key (`user`) |

### Article (`article`)
Represents a specific article/item variation that can be purchased. An article is a specific variant of a product (e.g., a particular size or colour).

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique article identifier |
| `name` | string | Article identifier (same as id) |
| `detail_desc` | string | Detailed article description |
| `partitionKey` | string | Partition key (`article`) |

### Product (`product`)
Represents a product that groups multiple article variations together.

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique product identifier |
| `name` | string | Product name |
| `partitionKey` | string | Partition key (`product`) |

### Category Nodes
Products are organized into various category hierarchies:

| Node Type | Description |
|-----------|-------------|
| `product_type` | Type of product (e.g., T-shirt, Trousers) |
| `product_group` | Product grouping |
| `colour_group` | Colour categorization (linked to articles) |
| `department` | Department (e.g., Menswear, Ladieswear) |
| `index_group` | Index grouping |

## Edge Types

### `purchased`
Represents a purchase transaction.

- **Direction**: `user` → `article`
- **Meaning**: Customer purchased the article
- **Properties**: May include transaction metadata

### `belongs_to`
Represents hierarchical relationships.

- **Direction**: Various
- **Relationships**:
  - `article` → `product` (article is a variant of product)
  - `article` → `colour_group` (article has this colour)
  - `product` → `product_type` (product is of this type)
  - `product_type` → `product_group` (type belongs to group)
  - `product` → `department` (product is in department)

## Graph Visualization

```
                    ┌─────────────┐
                    │    user     │
                    │  (customer) │
                    └──────┬──────┘
                           │
                           │ purchased
                           ▼
                    ┌─────────────┐
                    │   article   │
                    │  (variant)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │ belongs_to │            │ belongs_to
              ▼            │            ▼
       ┌────────────┐      │     ┌────────────┐
       │colour_group│      │     │  product   │
       └────────────┘      │     │   (base)   │
                           │     └──────┬─────┘
                           │            │
                           │            │ belongs_to
                           │            ▼
                           │  ┌─────────────────────┐
                           │  │                     │
                           ▼  ▼                     ▼
                    ┌────────────┐          ┌────────────┐
                    │product_type│          │ department │
                    └──────┬─────┘          └────────────┘
                           │
                           │ belongs_to
                           ▼
                    ┌────────────┐
                    │product_group│
                    └────────────┘
```

## Example Gremlin Queries

### Basic Node Queries

```groovy
// Get a user by ID
g.V().has('id', '<user_id>').valueMap(true)

// Get all users
g.V().hasLabel('user').limit(10).valueMap(true)

// Get an article by ID
g.V().has('id', '<article_id>').valueMap(true)

// Get a product by ID
g.V().has('id', '<product_id>').valueMap(true)
```

### Traversal Queries

```groovy
// Get articles purchased by a user
g.V().has('id', '<user_id>').out('purchased').valueMap(true)

// Count a user's purchases
g.V().has('id', '<user_id>').out('purchased').count()

// Get the product for an article
g.V().has('id', '<article_id>').out('belongs_to').hasLabel('product').valueMap(true)

// Get all articles for a product
g.V().has('id', '<product_id>').in('belongs_to').hasLabel('article').valueMap(true)

// Find users who purchased a specific article
g.V().has('id', '<article_id>').in('purchased').valueMap(true)
```

### Advanced Queries

```groovy
// Find products by name pattern
g.V().hasLabel('product').has('name', TextP.containing('shirt')).valueMap(true)

// Get product names for articles a user purchased
g.V().has('id', '<user_id>')
  .out('purchased')
  .out('belongs_to')
  .hasLabel('product')
  .dedup()
  .valueMap(true)

// Get all departments a user has purchased from
g.V().has('id', '<user_id>')
  .out('purchased')
  .out('belongs_to')
  .hasLabel('product')
  .out('belongs_to')
  .hasLabel('department')
  .dedup()
  .valueMap(true)

// Count articles per colour group for a user
g.V().has('id', '<user_id>')
  .out('purchased')
  .out('belongs_to')
  .hasLabel('colour_group')
  .groupCount()
  .by('name')
```

## Data Sources

The graph is populated from CSV files in the `/data` directory:

- `customers.csv` - Customer data → `user` nodes
- `articles.csv` - Article data → `article` nodes, `product` nodes, and category nodes
- `transactions_train.csv` - Purchase history → `purchased` edges
