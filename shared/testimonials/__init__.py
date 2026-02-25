"""
API для работы с отзывами и историями успеха (testimonials).
"""

from .testimonials_manager import (
    TestimonialsManager,
    TestimonialCategory,
    get_testimonials_manager
)

__all__ = ['TestimonialsManager', 'TestimonialCategory', 'get_testimonials_manager']
