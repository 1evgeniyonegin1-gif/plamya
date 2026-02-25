import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Package, ArrowLeft, ChevronRight, ExternalLink } from 'lucide-react'
import { AnimatePresence } from 'framer-motion'
import { productsApi, Product, Category, Line } from '../api/client'
import { ProductCard } from '../components/ProductCard'
import { ProductModal } from '../components/ProductModal'
import { Loading } from '../components/Loading'
import { useTelegram } from '../hooks/useTelegram'
import { motion, staggerContainer, staggerItem, AnimatedNumber, SPRING_SNAPPY } from '../lib/animations'

// Category emoji mapping
const CATEGORY_EMOJI: Record<string, string> = {
  'Коктейли ED/ED Smart': '🥤',
  'БАДы': '💊',
  'Красота и уход': '💄',
  'Адаптогены': '🧬',
  'Для детей': '👶',
  'Чай и напитки': '🍵',
  'Imperial Herb': '🌿',
}

export function Products() {
  const { haptic, openLink, showBackButton, hideBackButton } = useTelegram()
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [selectedLine, setSelectedLine] = useState<string | null>(null)
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [showAllProducts, setShowAllProducts] = useState(false)
  const handleBackRef = useRef<() => void>(() => {})

  // Fetch categories
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => productsApi.getCategories(),
  })

  // Fetch referral links (for store button)
  const { data: linksData } = useQuery({
    queryKey: ['referral-links'],
    queryFn: () => productsApi.getReferralLinks(),
  })
  const catalogLink = linksData?.data?.catalog || ''

  // Fetch lines for selected category
  const { data: linesData } = useQuery({
    queryKey: ['lines', selectedCategory],
    queryFn: () => productsApi.getLines(selectedCategory!),
    enabled: selectedCategory !== null && selectedLine === null && !search,
  })

  // Fetch products (when line selected, searching, or showing all)
  const shouldFetchProducts = selectedLine !== null || search.length > 0 || showAllProducts
  const { data: productsData, isLoading } = useQuery({
    queryKey: ['products', selectedCategory, selectedLine, search],
    queryFn: () => productsApi.getProducts({
      category: selectedCategory || undefined,
      line: selectedLine && selectedLine !== '__all__' ? selectedLine : undefined,
      search: search || undefined,
      limit: 100,
    }),
    enabled: shouldFetchProducts,
  })

  const categories = categoriesData?.data?.categories || []
  const lines = linesData?.data?.lines || []
  const products = productsData?.data?.products || []
  const referralLink = productsData?.data?.referral_catalog || ''

  // View modes
  const isProductsView = selectedLine !== null || search.length > 0 || showAllProducts
  const isLinesView = selectedCategory !== null && selectedLine === null && !search && !showAllProducts

  // Auto-select when category has only 1 line (skip lines screen)
  useEffect(() => {
    if (isLinesView && lines.length === 1) {
      setSelectedLine(lines[0].name)
    }
  }, [isLinesView, lines])

  // Handle back navigation
  const handleBack = useCallback(() => {
    haptic('light')
    if (isProductsView && selectedLine) {
      // If category had only 1 line, go straight back to categories
      if (lines.length <= 1) {
        setSelectedCategory(null)
        setSelectedLine(null)
        setShowAllProducts(false)
        setSearch('')
      } else {
        // Products → Lines
        setSelectedLine(null)
        setShowAllProducts(false)
      }
    } else {
      // Lines → Categories (or search/all → categories)
      setSelectedCategory(null)
      setSelectedLine(null)
      setShowAllProducts(false)
      setSearch('')
    }
  }, [isProductsView, selectedLine, lines.length, haptic])

  // Keep ref updated for BackButton callback
  handleBackRef.current = handleBack

  // Telegram BackButton integration
  useEffect(() => {
    const needsBack = isProductsView || isLinesView
    if (needsBack) {
      showBackButton(() => handleBackRef.current())
    } else {
      hideBackButton()
    }
    return () => hideBackButton()
  }, [isProductsView, isLinesView, showBackButton, hideBackButton])

  // Handle product click
  const handleProductClick = (product: Product) => {
    haptic('light')
    setSelectedProduct(product)
  }

  // Handle order click
  const handleOrderClick = async () => {
    if (!selectedProduct) return
    haptic('success')
    try {
      await productsApi.trackView(selectedProduct.key, true)
    } catch (e) {
      console.error('Failed to track view', e)
    }
    openLink(selectedProduct.referral_link || referralLink)
    setSelectedProduct(null)
  }

  // Handle category select → show lines
  const handleCategorySelect = (categoryName: string) => {
    haptic('light')
    setSelectedCategory(categoryName)
    setSelectedLine(null)
    setShowAllProducts(false)
    setSearch('')
  }

  // Handle line select → show products
  const handleLineSelect = (lineName: string) => {
    haptic('light')
    setSelectedLine(lineName)
  }

  // Handle search input
  const handleSearch = (value: string) => {
    setSearch(value)
    if (value.length > 0) {
      setSelectedCategory(null)
      setSelectedLine(null)
      setShowAllProducts(true)
    }
  }

  // Handle "All products" button
  const handleShowAll = () => {
    haptic('light')
    setShowAllProducts(true)
    setSelectedCategory(null)
    setSelectedLine(null)
    setSearch('')
  }

  // Handle "All products in category" from lines view
  const handleShowAllInCategory = () => {
    haptic('light')
    setSelectedLine('__all__')
  }

  if (isLoading && shouldFetchProducts && !products.length) {
    return <Loading message="Загрузка каталога..." />
  }

  // Breadcrumb text for back button
  const backLabel = isProductsView && selectedLine
    ? `Назад к ${selectedCategory}`
    : 'Назад к категориям'

  return (
    <div className="p-4 pb-8">
      <AnimatePresence mode="wait">
        {isProductsView ? (
          <motion.div
            key="products-view"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            transition={SPRING_SNAPPY}
          >
            {/* ===== PRODUCTS VIEW ===== */}

            {/* Back button */}
            <motion.button
              onClick={handleBack}
              className="flex items-center gap-2 text-amber-soft mb-4 active:opacity-70 transition-opacity"
              whileTap={{ scale: 0.96 }}
            >
              <ArrowLeft size={20} />
              <span className="text-sm font-medium">{backLabel}</span>
            </motion.button>

            {/* Header */}
            <div className="mb-4">
              <h1 className="text-xl font-bold text-cream flex items-center gap-2">
                {selectedCategory && (
                  <span className="text-2xl">{CATEGORY_EMOJI[selectedCategory] || '📦'}</span>
                )}
                {selectedLine && selectedLine !== '__all__'
                  ? selectedLine
                  : selectedCategory || (search ? `Поиск: ${search}` : 'Все товары')}
              </h1>
              <p className="text-sand text-sm mt-1">
                <AnimatedNumber value={productsData?.data?.total || 0} /> товаров
              </p>
            </div>

            {/* Search within products */}
            <div className="relative mb-4">
              <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-stone" />
              <input
                type="text"
                placeholder="Поиск..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onFocus={() => haptic('light')}
                className="input pl-11"
              />
            </div>

            {/* Products Grid */}
            {products.length > 0 ? (
              <motion.div
                className="grid grid-cols-2 gap-3"
                variants={staggerContainer}
                initial="hidden"
                animate="show"
              >
                {products.map((product) => (
                  <motion.div key={product.key} variants={staggerItem}>
                    <ProductCard
                      product={product}
                      onClick={() => handleProductClick(product)}
                    />
                  </motion.div>
                ))}
              </motion.div>
            ) : (
              <div className="card text-center py-12">
                <Package size={48} className="mx-auto text-stone mb-4" />
                <p className="text-sand">
                  {search ? 'Ничего не найдено' : 'Нет товаров'}
                </p>
              </div>
            )}
          </motion.div>
        ) : isLinesView ? (
          <motion.div
            key="lines-view"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            transition={SPRING_SNAPPY}
          >
            {/* ===== LINES VIEW ===== */}

            {/* Back button */}
            <motion.button
              onClick={handleBack}
              className="flex items-center gap-2 text-amber-soft mb-4 active:opacity-70 transition-opacity"
              whileTap={{ scale: 0.96 }}
            >
              <ArrowLeft size={20} />
              <span className="text-sm font-medium">Назад к категориям</span>
            </motion.button>

            {/* Category header */}
            <div className="mb-5">
              <h1 className="text-2xl font-bold text-cream flex items-center gap-2">
                <span className="text-3xl">{CATEGORY_EMOJI[selectedCategory!] || '📦'}</span>
                {selectedCategory}
              </h1>
              <p className="text-sand text-sm mt-1">
                Выберите линейку
              </p>
            </div>

            {/* Lines Grid — card layout */}
            {lines.length > 0 ? (
              <motion.div
                className="grid grid-cols-2 gap-3 mb-4"
                variants={staggerContainer}
                initial="hidden"
                animate="show"
              >
                {lines.map((line: Line) => (
                  <motion.button
                    key={line.name}
                    variants={staggerItem}
                    whileTap={{ scale: 0.96 }}
                    transition={SPRING_SNAPPY}
                    onClick={() => handleLineSelect(line.name)}
                    className="card p-4 text-left"
                  >
                    <div className="w-full aspect-[4/3] rounded-lg bg-smoke mb-3 flex items-center justify-center overflow-hidden">
                      {line.image_url ? (
                        <img
                          src={line.image_url}
                          alt={line.name}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <Package size={28} className="text-stone" />
                      )}
                    </div>
                    <h3 className="text-xs font-semibold text-cream leading-tight line-clamp-2 mb-1">
                      {line.name}
                    </h3>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-sand">
                        {line.product_count} товаров
                      </span>
                      <ChevronRight size={14} className="text-stone" />
                    </div>
                  </motion.button>
                ))}
              </motion.div>
            ) : (
              <div className="card text-center py-8 mb-4">
                <p className="text-sand text-sm">Загрузка линеек...</p>
              </div>
            )}

            {/* Show all products in category */}
            <motion.button
              onClick={handleShowAllInCategory}
              whileTap={{ scale: 0.97 }}
              transition={SPRING_SNAPPY}
              className="btn btn-secondary w-full flex items-center justify-center gap-2"
            >
              <Package size={18} />
              <span>Все товары категории</span>
            </motion.button>
          </motion.div>
        ) : (
          <motion.div
            key="categories-view"
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 30 }}
            transition={SPRING_SNAPPY}
          >
            {/* ===== CATEGORIES VIEW ===== */}

            {/* Header */}
            <div className="mb-5">
              <h1 className="text-2xl font-bold text-gradient-gold mb-1">
                Продукция NL
              </h1>
              <p className="text-sand text-sm">
                Выберите категорию
              </p>
            </div>

            {/* Search */}
            <div className="relative mb-5">
              <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-stone" />
              <input
                type="text"
                placeholder="Поиск по всем товарам..."
                value={search}
                onChange={(e) => handleSearch(e.target.value)}
                onFocus={() => haptic('light')}
                className="input pl-11"
              />
            </div>

            {/* Store button */}
            {catalogLink && (
              <motion.button
                onClick={() => {
                  haptic('light')
                  openLink(catalogLink)
                }}
                whileTap={{ scale: 0.97 }}
                transition={SPRING_SNAPPY}
                className="w-full mb-4 p-4 rounded-2xl bg-gradient-to-r from-amber/20 to-amber-deep/20 border border-amber/30 flex items-center gap-3"
              >
                <div className="w-10 h-10 rounded-xl bg-amber/20 flex items-center justify-center shrink-0">
                  <ExternalLink size={20} className="text-amber-soft" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="text-sm font-semibold text-cream">Магазин NL</h3>
                  <p className="text-xs text-sand">Перейти в онлайн-магазин</p>
                </div>
                <ChevronRight size={16} className="text-stone" />
              </motion.button>
            )}

            {/* Categories Grid */}
            <motion.div
              className="grid grid-cols-2 gap-3 mb-4"
              variants={staggerContainer}
              initial="hidden"
              animate="show"
            >
              {categories.map((cat: Category) => (
                <motion.button
                  key={cat.name}
                  variants={staggerItem}
                  whileTap={{ scale: 0.96 }}
                  transition={SPRING_SNAPPY}
                  onClick={() => handleCategorySelect(cat.name)}
                  className="card p-4 text-left"
                >
                  <div className="text-3xl mb-2">
                    {CATEGORY_EMOJI[cat.name] || '📦'}
                  </div>
                  <h3 className="text-sm font-semibold text-cream leading-tight mb-1">
                    {cat.name}
                  </h3>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-sand">
                      {cat.product_count} товаров
                    </span>
                    <ChevronRight size={14} className="text-stone" />
                  </div>
                </motion.button>
              ))}
            </motion.div>

            {/* Show all products button */}
            <motion.button
              onClick={handleShowAll}
              whileTap={{ scale: 0.97 }}
              transition={SPRING_SNAPPY}
              className="btn btn-secondary w-full flex items-center justify-center gap-2"
            >
              <Package size={18} />
              <span>Все товары ({categories.reduce((sum: number, c: Category) => sum + c.product_count, 0)})</span>
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Product Modal */}
      <AnimatePresence>
        {selectedProduct && (
          <ProductModal
            product={selectedProduct}
            onClose={() => {
              haptic('light')
              setSelectedProduct(null)
            }}
            onOrderClick={handleOrderClick}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
