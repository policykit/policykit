
def format_vote_on(action):
    user = action.initiator
    userId: str = user.username
    discord_id, _ = userId.split(":")
    message_text = f"""
    <@{discord_id}> proposed {action}
    vote by reacting either 👍 or 👎 on this message
    """
    
    try:
        desc = action.description
        message_text += f"""Description: {desc}"""
    except:
        pass
    message_text += "Thanks Jason love ya dude 💖"
