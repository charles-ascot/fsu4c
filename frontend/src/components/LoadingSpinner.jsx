export default function LoadingSpinner({ size = 6 }) {
  return (
    <div
      className={`w-${size} h-${size} rounded-full border-2 border-transparent animate-spin`}
      style={{ borderTopColor: 'var(--cyan)', borderRightColor: 'rgba(0,212,255,0.3)' }}
    />
  )
}
