import cds from '@sap/cds'

const BASIC_AUTH_USER = process.env.BASIC_AUTH_USER
const BASIC_AUTH_PASSWORD = process.env.BASIC_AUTH_PASSWORD

if (!BASIC_AUTH_USER || !BASIC_AUTH_PASSWORD) {
  console.error('ERROR: BASIC_AUTH_USER and BASIC_AUTH_PASSWORD environment variables are required.')
  process.exit(1)
}

const EXPECTED = 'Basic ' + Buffer.from(`${BASIC_AUTH_USER}:${BASIC_AUTH_PASSWORD}`).toString('base64')

cds.on('bootstrap', app => {
  app.use((req, res, next) => {
    if (req.path === '/' || req.path.endsWith('$metadata')) return next()

    if (req.headers.authorization === EXPECTED) return next()

    res.set('WWW-Authenticate', 'Basic realm="Altura Service Locator"')
    res.status(401).json({ error: { code: '401', message: 'Unauthorized' } })
  })
})

export default cds.server
