import { useState } from 'react'
import { Package } from 'lucide-react'
import Tilt from 'react-parallax-tilt'
import { Product } from '../api/client'
import { motion, AnimatedNumber, SPRING_SNAPPY } from '../lib/animations'

interface ProductCardProps {
  product: Product
  onClick: () => void
}

export function ProductCard({ product, onClick }: ProductCardProps) {
  const [imageLoaded, setImageLoaded] = useState(false)

  return (
    <Tilt
      tiltMaxAngleX={8}
      tiltMaxAngleY={8}
      glareEnable={true}
      glareMaxOpacity={0.15}
      glareColor="rgba(245,158,11,0.2)"
      glareBorderRadius="1rem"
      scale={1.02}
      perspective={1000}
      transitionSpeed={400}
    >
      <motion.div
        className="product-card"
        onClick={onClick}
        whileTap={{ scale: 0.96 }}
        transition={SPRING_SNAPPY}
      >
        {/* Image */}
        <div className="aspect-[3/4] rounded-xl bg-smoke mb-3 flex items-center justify-center overflow-hidden">
          {product.image_url ? (
            <motion.img
              src={`${product.image_url}?index=1`}
              alt={product.name}
              className="w-full h-full object-cover object-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: imageLoaded ? 1 : 0 }}
              transition={{ duration: 0.4 }}
              onLoad={() => setImageLoaded(true)}
              onError={(e) => {
                e.currentTarget.style.display = 'none'
                e.currentTarget.parentElement?.classList.add('show-fallback')
              }}
            />
          ) : (
            <Package size={32} className="text-stone" />
          )}
        </div>

        {/* Info */}
        <h3 className="text-sm font-medium text-cream line-clamp-2 mb-2">
          {product.name}
        </h3>

        <div className="flex items-center justify-between">
          <AnimatedNumber
            value={product.price}
            prefix="₽"
            className="text-amber-soft font-semibold"
          />
          <span className="text-xs text-stone">
            {product.pv} PV
          </span>
        </div>
      </motion.div>
    </Tilt>
  )
}
