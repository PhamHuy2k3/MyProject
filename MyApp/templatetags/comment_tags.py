from django import template
from MyApp.models import CommentInteraction

register = template.Library()

@register.filter
def get_comment_likes(comment):
    """Returns the total number of likes for a comment."""
    if hasattr(comment, 'like_count'):
        return comment.like_count
    return comment.interactions.filter(is_like=True).count()

@register.filter
def get_comment_dislikes(comment):
    if hasattr(comment, 'dislike_count'):
        return comment.dislike_count
    return comment.interactions.filter(is_like=False).count()

@register.simple_tag
def get_user_interaction(comment, user):
    """Returns 'like', 'dislike', or None for the given user on the comment."""
    if not user.is_authenticated:
        return None
    interaction = comment.interactions.filter(user=user).first()
    if interaction:
        return 'like' if interaction.is_like else 'dislike'
    return None
