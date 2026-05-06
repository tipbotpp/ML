from fastapi import APIRouter, Depends

from app.dependencies import verify_internal_secret
from app.services.logger import get_logger
from app.api.moderation import moderation_cache
from app.api.tts import tts_cache
from app.services.image_generation import image_cache

logger = get_logger().bind(module="admin")

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/cache/stats")
async def get_cache_stats(_=Depends(verify_internal_secret)):
    moderation_cache.cleanup_expired()
    tts_cache.cleanup_expired()
    image_cache.cleanup_expired()
    
    stats = {
        "moderation": moderation_cache.get_stats(),
        "tts": tts_cache.get_stats(),
        "image": image_cache.get_stats(),
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    logger.info("admin.cache_stats", stats=stats)
    return stats


@router.post("/cache/clear")
async def clear_cache(service: str = None, _=Depends(verify_internal_secret)):
    if service is None:
        m_count = moderation_cache.clear()
        t_count = tts_cache.clear()
        i_count = image_cache.clear()
        logger.info(
            "admin.cache_clear_all",
            moderation=m_count,
            tts=t_count,
            image=i_count,
        )
        return {
            "message": "All caches cleared",
            "moderation_entries": m_count,
            "tts_entries": t_count,
            "image_entries": i_count,
        }
    elif service == "moderation":
        count = moderation_cache.clear()
        logger.info("admin.cache_clear", service="moderation", count=count)
        return {"message": "Moderation cache cleared", "entries_removed": count}
    elif service == "tts":
        count = tts_cache.clear()
        logger.info("admin.cache_clear", service="tts", count=count)
        return {"message": "TTS cache cleared", "entries_removed": count}
    elif service == "image":
        count = image_cache.clear()
        logger.info("admin.cache_clear", service="image", count=count)
        return {"message": "Image cache cleared", "entries_removed": count}
    else:
        logger.warning("admin.cache_clear_invalid", service=service)
        return {"error": f"Unknown service: {service}"}, 400


@router.post("/cache/cleanup")
async def cleanup_expired_cache(_=Depends(verify_internal_secret)):
    m_removed = moderation_cache.cleanup_expired()
    t_removed = tts_cache.cleanup_expired()
    i_removed = image_cache.cleanup_expired()
    
    total_removed = m_removed + t_removed + i_removed
    logger.info(
        "admin.cache_cleanup",
        moderation=m_removed,
        tts=t_removed,
        image=i_removed,
        total=total_removed,
    )
    
    return {
        "moderation_removed": m_removed,
        "tts_removed": t_removed,
        "image_removed": i_removed,
        "total_removed": total_removed,
    }


@router.get("/cache/detailed")
async def get_detailed_cache_info(_=Depends(verify_internal_secret)):
    moderation_cache.cleanup_expired()
    tts_cache.cleanup_expired()
    image_cache.cleanup_expired()
    
    return {
        "services": {
            "moderation": {
                "stats": moderation_cache.get_stats(),
                "priority": "Medium - 30min TTL, 30% memory",
            },
            "tts": {
                "stats": tts_cache.get_stats(),
                "priority": "High - 24hr TTL, 50% memory",
            },
            "image": {
                "stats": image_cache.get_stats(),
                "priority": "Low - 1hr TTL, 20% memory",
            },
        },
        "recommendations": _get_cache_recommendations(moderation_cache, tts_cache, image_cache),
    }


def _get_cache_recommendations(mod_cache, tts_cache, img_cache) -> list[str]:
    recommendations = []
    
    mod_stats = mod_cache.get_stats()
    if mod_stats["hit_rate"] < 0.5:
        recommendations.append("Moderation cache hit rate is low - consider longer TTL")
    if mod_stats["active_entries"] > mod_stats["max_entries"] * 0.9:
        recommendations.append("Moderation cache is nearly full - consider cleanup")
    
    tts_stats = tts_cache.get_stats()
    if tts_stats["total_evictions"] > tts_stats["total_sets"] * 0.1:
        recommendations.append("TTS cache has high eviction rate - increase max memory")
    
    img_stats = img_cache.get_stats()
    if img_stats["total_size_mb"] > (img_cache._max_memory_mb or 100) * 0.8:
        recommendations.append("Image cache memory usage is high - consider cleanup")
    
    if not recommendations:
        recommendations.append("Cache configuration is optimal")
    
    return recommendations


@router.get("/health/detailed")
async def detailed_health(_=Depends(verify_internal_secret)):
    moderation_cache.cleanup_expired()
    tts_cache.cleanup_expired()
    image_cache.cleanup_expired()
    
    return {
        "status": "ok",
        "cache": {
            "enabled": True,
            "stats": {
                "moderation": moderation_cache.get_stats(),
                "tts": tts_cache.get_stats(),
                "image": image_cache.get_stats(),
            },
        }
    }
