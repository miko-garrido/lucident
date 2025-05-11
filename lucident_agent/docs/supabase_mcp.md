# Supabase MCP Documentation

## AI Prompts

Prompts for working with Supabase using AI-powered IDE tools

---

We've curated a selection of prompts to help you work with Supabase using your favorite AI-powered IDE tools, such as Cursor or GitHub Copilot.

### How to use

Copy the prompt to a file in your repo.

Use the "include file" feature from your AI tool to include the prompt when chatting with your AI assistant. For example, in Cursor, add them as project rules, with GitHub Copilot, use `#<filename>`, and in Zed, use `/file`.

### Prompts

- Bootstrap Next.js app with Supabase Auth
- Writing Supabase Edge Functions
- Database: Create RLS policies
- Database: Create functions
- Database: Create migration
- Postgres SQL Style Guide

---

## Bootstrap Next.js app with Supabase Auth

### How to use

Copy the prompt to a file in your repo.

Use the "include file" feature from your AI tool to include the prompt when chatting with your AI assistant. For example, with GitHub Copilot, use `#<filename>`, in Cursor, use `@Files`, and in Zed, use `/file`.

#### Prompt

```
<Insert the full prompt content here if needed>
```

---

## Code Format SQL (Claude code)

1. Create a `.mcp.json` file in your project root if it doesn't exist.
2. Add the following configuration:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "<personal-access-token>"
      ]
    }
  }
}
```
Replace `<personal-access-token>` with your personal access token.
3. Save the configuration file.
4. Restart Claude code to apply the new configuration.

#### Next steps

Your AI tool is now connected to Supabase using MCP. Try asking your AI assistant to create a new project, create a table, or fetch project config.

For a full list of tools available, see the GitHub README. If you experience any issues, submit a bug report.

---

## Refine App Tutorial

### Initialize a refine app

We can use create refine-app command to initialize an app. Run the following in the terminal:

```sh
npm create refine-app@latest -- --preset refine-supabase
```

In the above command, we are using the `refine-supabase` preset which chooses the Supabase supplementary package for our app. We are not using any UI framework, so we'll have a headless UI with plain React and CSS styling.

The `refine-supabase` preset installs the `@refinedev/supabase` package which out-of-the-box includes the Supabase dependency: supabase-js.

We also need to install `@refinedev/react-hook-form` and `react-hook-form` packages that allow us to use React Hook Form inside refine apps. Run:

```sh
npm install @refinedev/react-hook-form react-hook-form
```

With the app initialized and packages installed, at this point before we begin discussing refine concepts, let's try running the app:

```sh
cd app-name
npm run dev
```

We should have a running instance of the app with a Welcome page at `http://localhost:5173`.

Let's move ahead to understand the generated code now.

---

## RedwoodJS Tutorial

A Redwood application is split into two parts: a frontend and a backend. This is represented as two node projects within a single monorepo.

The frontend project is called **`web`** and the backend project is called **`api`**. For clarity, we will refer to these in prose as **"sides,"** that is, the `web side` and the `api side`. They are separate projects because code on the `web side` will end up running in the user's browser while code on the `api side` will run on a server somewhere.

Important: When this guide refers to "API," that means the Supabase API and when it refers to `api side`, that means the RedwoodJS `api side`.

The **`api side`** is an implementation of a GraphQL API. The business logic is organized into "services" that represent their own internal API and can be called both from external GraphQL requests and other internal services.

The **`web side`** is a React app. It communicates with the `api side` via GraphQL.

You will want to refrain from running any `yarn rw prisma migrate` commands and also double check your build commands on deployment to ensure Prisma won't reset your database. Prisma currently doesn't support cross-schema foreign keys, so introspecting the schema fails due to how your Supabase `public` schema references the `auth.users` table.

RedwoodJS requires Node.js `>= 14.x <= 16.x` and Yarn `>= 1.15`.

Make sure you have installed yarn since RedwoodJS relies on it to manage its packages in workspaces for its `web` and `api` "sides."