import { useState } from 'react'
import { X, Package, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import { AnimatePresence } from 'framer-motion'
import { Product } from '../api/client'
import { useTelegram } from '../hooks/useTelegram'
import { motion, AnimatedNumber, SPRING_SNAPPY } from '../lib/animations'

interface ProductModalProps {
  product: Product
  onClose: () => void
  onOrderClick: () => void
}

export function ProductModal({ product, onClose, onOrderClick }: ProductModalProps) {
  const { haptic } = useTelegram()
  const [imageIndex, setImageIndex] = useState(0)
  const imageCount = product.image_count || (product.image_url ? 1 : 0)
  const hasMultiple = imageCount > 1

  const getImageUrl = (idx: number) => {
    if (!product.image_url) return null
    // image_url is like /api/v1/products/{key}/image
    return `${product.image_url}?index=${idx + 1}`
  }

  const handleSwipe = (direction: number) => {
    if (!hasMultiple) return
    const next = imageIndex + direction
    if (next >= 0 && next < imageCount) {
      haptic('light')
      setImageIndex(next)
    }
  }

  const handleOrder = () => {
    haptic('success')
    onOrderClick()
  }

  return (
    <>
      {/* Overlay */}
      <motion.div
        className="fixed inset-0 z-50 bg-obsidian/95 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        onClick={onClose}
      />

      {/* Modal content */}
      <motion.div
        className="fixed inset-x-0 bottom-0 z-50 modal-content"
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={SPRING_SNAPPY}
        drag="y"
        dragConstraints={{ top: 0, bottom: 0 }}
        dragElastic={{ top: 0, bottom: 0.4 }}
        onDragEnd={(_, info) => {
          if (info.offset.y > 150 || info.velocity.y > 500) {
            onClose()
          }
        }}
      >
        {/* Drag handle */}
        <div className="drag-handle" />

        {/* Scrollable area */}
        <div className="overflow-y-auto px-6 pt-3 pb-2" style={{ maxHeight: 'calc(90vh - 80px)' }}>
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-cream pr-4">
              {product.name}
            </h2>
            <motion.button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-smoke transition-colors flex-shrink-0"
              whileTap={{ scale: 0.9 }}
              transition={SPRING_SNAPPY}
            >
              <X size={20} className="text-stone" />
            </motion.button>
          </div>

          {/* Image carousel */}
          <motion.div
            className="relative rounded-xl bg-smoke mb-4 overflow-hidden max-h-[35vh] aspect-square"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
          >
            {product.image_url ? (
              <>
                <AnimatePresence mode="wait" initial={false}>
                  <motion.img
                    key={imageIndex}
                    src={getImageUrl(imageIndex)!}
                    alt={product.name}
                    className="w-full h-full object-cover object-center"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    draggable={false}
                  />
                </AnimatePresence>

                {/* Swipe overlay for carousel */}
                {hasMultiple && (
                  <motion.div
                    className="absolute inset-0"
                    drag="x"
                    dragConstraints={{ left: 0, right: 0 }}
                    dragElastic={0.3}
                    onDragEnd={(_, info) => {
                      if (info.offset.x < -50 || info.velocity.x < -300) {
                        handleSwipe(1)
                      } else if (info.offset.x > 50 || info.velocity.x > 300) {
                        handleSwipe(-1)
                      }
                    }}
                  />
                )}

                {/* Arrow buttons */}
                {hasMultiple && imageIndex > 0 && (
                  <button
                    onClick={() => handleSwipe(-1)}
                    className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-obsidian/60 flex items-center justify-center"
                  >
                    <ChevronLeft size={18} className="text-cream" />
                  </button>
                )}
                {hasMultiple && imageIndex < imageCount - 1 && (
                  <button
                    onClick={() => handleSwipe(1)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-obsidian/60 flex items-center justify-center"
                  >
                    <ChevronRight size={18} className="text-cream" />
                  </button>
                )}

                {/* Dot indicators */}
                {hasMultiple && (
                  <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5">
                    {Array.from({ length: imageCount }).map((_, i) => (
                      <button
                        key={i}
                        onClick={() => { haptic('light'); setImageIndex(i) }}
                        className={`w-2 h-2 rounded-full transition-all ${
                          i === imageIndex
                            ? 'bg-amber w-4'
                            : 'bg-cream/40'
                        }`}
                      />
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Package size={48} className="text-stone" />
              </div>
            )}
          </motion.div>

          {/* Info */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <AnimatedNumber
                value={product.price}
                prefix="₽"
                className="text-2xl font-bold text-amber-soft"
              />
              <span className="text-sand">
                {product.pv} PV
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="category-pill text-xs">
                {product.category}
              </span>
            </div>

            {product.price_per_portion && (
              <p className="text-sm text-sand">
                ₽{product.price_per_portion.toFixed(0)} за порцию
              </p>
            )}

            {product.description && (
              <p className="text-sm text-sand mt-1">
                {product.description}
              </p>
            )}
            {!product.description && (
              <p className="text-sm text-stone italic mt-1">
                {product.category}
              </p>
            )}
          </div>
        </div>

        {/* CTA — fixed at bottom */}
        <div className="px-6 pb-6 pt-3">
          <motion.button
            onClick={handleOrder}
            className="btn btn-success w-full flex items-center justify-center gap-2 py-3 text-base font-bold"
            whileTap={{ scale: 0.96 }}
            transition={SPRING_SNAPPY}
          >
            <ExternalLink size={20} />
            <span>Заказать на сайте NL</span>
          </motion.button>
        </div>
      </motion.div>
    </>
  )
}
