# ChatControl Linking Guide

## What Is Linking

Linking binds a Minecraft player to a Twitch streamer account. After linking, ChatControl knows which Minecraft player belongs to which streamer.

## Prerequisites

1. Twitch account logged in via OAuth
2. Email verified (see below)
3. Minecraft server running with ChatControl Core
4. Bridge connected and authenticated

## How to Link

### Step 1: Verify Your Email
After first login, you'll be prompted to verify your email. Check your inbox for a confirmation link.

### Step 2: Generate a Link Code
On the dashboard, click "Link Minecraft Account". A 6-digit code will appear (valid for 60 seconds).

### Step 3: Enter Code in Minecraft
In your Minecraft server chat, type:
```
/chatcontrol link 583921
```

### Step 4: Done!
The system will validate the code and link your Minecraft player to your Twitch account.

## Unlinking

In Minecraft chat:
```
/chatcontrol unlink
```

Or on the dashboard, click "Desvincular".

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Email not verified" | Check your inbox for verification email |
| "Code expired" | Generate a new code (codes last 60 seconds) |
| "Invalid code" | Make sure you typed the code correctly |
| "Already linked" | Unlink first, then link again |
| "Bridge not connected" | Start the Bridge and Minecraft server |
