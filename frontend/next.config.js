/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
    dirs: ['src'], // Only run ESLint on the 'src' directory
  },
  experimental: {
    eslint: {
      // Disable ESLint during builds
      ignoreDuringBuilds: true,
    }
  }
}

module.exports = nextConfig