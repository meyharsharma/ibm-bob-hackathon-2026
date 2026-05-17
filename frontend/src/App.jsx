import React, { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'

const API = '/api'

// ---------- textures ----------

const textureCache = new Map()

function rng(seed) {
  let s = seed || 1
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}

function makeFacadeTexture(seed, isGlass) {
  const key = `fac:${seed}:${isGlass}`
  if (textureCache.has(key)) return textureCache.get(key)
  const c = document.createElement('canvas')
  c.width = 256; c.height = 512
  const ctx = c.getContext('2d')
  const wallGrad = ctx.createLinearGradient(0, 0, 0, c.height)
  if (isGlass) {
    wallGrad.addColorStop(0, '#5d7da6')
    wallGrad.addColorStop(1, '#3d5778')
  } else {
    wallGrad.addColorStop(0, '#cfd4dc')
    wallGrad.addColorStop(1, '#a6abb8')
  }
  ctx.fillStyle = wallGrad
  ctx.fillRect(0, 0, c.width, c.height)
  const floors = 28
  const cols = 14
  const floorH = c.height / floors
  const winW = c.width / cols
  const r = rng(seed)
  for (let f = 0; f < floors; f++) {
    const fy = f * floorH
    for (let col = 0; col < cols; col++) {
      const wx = col * winW
      const sky = r()
      if (isGlass) {
        ctx.fillStyle = `rgba(${60 + Math.floor(sky * 40)}, ${100 + Math.floor(sky * 60)}, ${160 + Math.floor(sky * 80)}, 0.95)`
      } else {
        ctx.fillStyle = `rgba(${130 + Math.floor(sky * 50)}, ${160 + Math.floor(sky * 40)}, ${190 + Math.floor(sky * 40)}, 0.92)`
      }
      const inset = 1.6
      ctx.fillRect(wx + inset, fy + inset, winW - inset * 2, floorH - inset * 2)
    }
    ctx.fillStyle = 'rgba(40,40,55,0.6)'
    ctx.fillRect(0, fy, c.width, 1.2)
  }
  ctx.fillStyle = 'rgba(40,40,55,0.55)'
  for (let col = 0; col <= cols; col++) {
    ctx.fillRect(col * winW - 0.5, 0, 1, c.height)
  }
  const tex = new THREE.CanvasTexture(c)
  tex.wrapS = THREE.RepeatWrapping
  tex.wrapT = THREE.RepeatWrapping
  tex.anisotropy = 8
  textureCache.set(key, tex)
  return tex
}

function makeSkyDome() {
  const c = document.createElement('canvas')
  c.width = 4; c.height = 1024
  const ctx = c.getContext('2d')
  const g = ctx.createLinearGradient(0, 0, 0, 1024)
  g.addColorStop(0.0, '#6fb0ff')
  g.addColorStop(0.45, '#9ccdff')
  g.addColorStop(0.75, '#d7e7f7')
  g.addColorStop(1.0, '#f4ead8')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, 4, 1024)
  const tex = new THREE.CanvasTexture(c)
  return new THREE.Mesh(new THREE.SphereGeometry(900, 32, 16), new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, depthWrite: false }))
}

function makeClouds() {
  const g = new THREE.Group()
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const ctx = c.getContext('2d')
  const grad = ctx.createRadialGradient(64, 64, 10, 64, 64, 60)
  grad.addColorStop(0, 'rgba(255,255,255,0.95)')
  grad.addColorStop(0.6, 'rgba(255,255,255,0.35)')
  grad.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, 128, 128)
  const tex = new THREE.CanvasTexture(c)
  for (let i = 0; i < 24; i++) {
    const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.7, depthWrite: false }))
    const a = Math.random() * Math.PI * 2
    const r = 250 + Math.random() * 220
    m.position.set(Math.cos(a) * r, 90 + Math.random() * 40, Math.sin(a) * r)
    const s = 80 + Math.random() * 100
    m.scale.set(s, s * 0.5, 1)
    g.add(m)
  }
  return g
}

// ---------- buildings (dynamic height) ----------

function makeFacadeMaterial(b, isGlass) {
  const tex = makeFacadeTexture((b.windows_seed || 1), isGlass)
  const matColor = new THREE.Color(b.color[0], b.color[1], b.color[2])
  return new THREE.MeshStandardMaterial({
    color: matColor.clone().multiplyScalar(isGlass ? 0.7 : 0.9),
    map: tex,
    roughness: isGlass ? 0.18 : 0.6,
    metalness: isGlass ? 0.55 : 0.15,
  })
}

function addPlinth(group, w, d, building) {
  const m = new THREE.Mesh(
    new THREE.BoxGeometry(w * 1.06, 0.35, d * 1.06),
    new THREE.MeshStandardMaterial({ color: 0x4a4f5d, roughness: 0.85 })
  )
  m.position.y = 0.175
  m.receiveShadow = true
  m.userData.building = building
  group.add(m)
}

function addTierBox(group, w, h, d, baseY, baseMat, building) {
  const sx = Math.max(1, Math.round(w / 1.0))
  const sy = Math.max(1, Math.round(h / 1.2))
  const m = baseMat.clone()
  m.map = baseMat.map.clone()
  m.map.needsUpdate = true
  m.map.wrapS = m.map.wrapT = THREE.RepeatWrapping
  m.map.repeat.set(sx, sy)
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m)
  mesh.position.y = baseY + h / 2
  mesh.castShadow = true
  mesh.receiveShadow = true
  mesh.userData.building = building
  group.add(mesh)
  return mesh
}

function addCrown(group, w, d, baseY, style, color, building) {
  if (style === 'spire') {
    const cap = new THREE.Mesh(
      new THREE.BoxGeometry(w * 0.7, 0.8, d * 0.7),
      new THREE.MeshStandardMaterial({ color: 0x55606d, roughness: 0.8 })
    )
    cap.position.y = baseY + 0.4
    cap.castShadow = true
    cap.userData.building = building
    group.add(cap)
    const spire = new THREE.Mesh(
      new THREE.ConeGeometry(Math.min(w, d) * 0.25, 4.5, 8),
      new THREE.MeshStandardMaterial({ color: 0xb8c4d8, metalness: 0.6, roughness: 0.3 })
    )
    spire.position.y = baseY + 0.8 + 2.25
    spire.castShadow = true
    spire.userData.building = building
    group.add(spire)
    const blink = new THREE.Mesh(
      new THREE.SphereGeometry(0.18, 10, 10),
      new THREE.MeshStandardMaterial({ color: 0xff3344, emissive: 0xff3344, emissiveIntensity: 1.6 })
    )
    blink.position.y = baseY + 0.8 + 4.5 + 1.5
    blink.userData.blink = true
    blink.userData.building = building
    group.add(blink)
  } else if (style === 'dome') {
    const dome = new THREE.Mesh(
      new THREE.SphereGeometry(Math.min(w, d) * 0.45, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2),
      new THREE.MeshStandardMaterial({ color: new THREE.Color(color[0], color[1], color[2]), roughness: 0.4, metalness: 0.4 })
    )
    dome.position.y = baseY
    dome.castShadow = true
    dome.userData.building = building
    group.add(dome)
  } else {
    const mech = new THREE.Mesh(
      new THREE.BoxGeometry(w * 0.55, 0.9, d * 0.55),
      new THREE.MeshStandardMaterial({ color: 0x6a707d, roughness: 0.85 })
    )
    mech.position.y = baseY + 0.45
    mech.castShadow = true
    mech.userData.building = building
    group.add(mech)
  }
}

function addPitchedRoof(group, w, d, baseY, building) {
  const roof = new THREE.Mesh(
    new THREE.ConeGeometry(Math.min(w, d) * 0.78, 1.4, 4),
    new THREE.MeshStandardMaterial({ color: 0x6a3b2a, roughness: 0.9 })
  )
  roof.position.y = baseY + 0.7
  roof.rotation.y = Math.PI / 4
  roof.castShadow = true
  roof.userData.building = building
  group.add(roof)
}

function buildBuilding(b, heightOverride) {
  const group = new THREE.Group()
  const r = rng(b.windows_seed || 1)
  const height = heightOverride != null ? heightOverride : b.height
  const isTall = height > 14
  const isGlass = isTall && r() < 0.55
  const baseMat = makeFacadeMaterial(b, isGlass)
  addPlinth(group, b.width, b.depth, b)
  if (height < 1.0) {
    // dormant plot — just plinth
  } else if (isTall) {
    const h1 = height * 0.62
    const h2 = height * 0.26
    const h3 = height * 0.12
    addTierBox(group, b.width, h1, b.depth, 0, baseMat, b)
    const w2 = b.width * 0.82, d2 = b.depth * 0.82
    addTierBox(group, w2, h2, d2, h1, baseMat, b)
    const w3 = b.width * 0.62, d3 = b.depth * 0.62
    addTierBox(group, w3, h3, d3, h1 + h2, baseMat, b)
    const style = r() < 0.4 ? 'spire' : r() < 0.6 ? 'dome' : 'mech'
    addCrown(group, w3, d3, height, style, b.color, b)
  } else if (height > 6) {
    addTierBox(group, b.width, height, b.depth, 0, baseMat, b)
    addCrown(group, b.width, b.depth, height, 'mech', b.color, b)
  } else {
    addTierBox(group, b.width, height, b.depth, 0, baseMat, b)
    if (b.roof === 'pitched') addPitchedRoof(group, b.width, b.depth, height, b)
  }
  group.position.set(b.x, 0, b.z)
  group.rotation.y = (b.windows_seed % 4) * (Math.PI / 180) * 0.6
  group.userData.building = b
  return group
}

// ---------- flythrough ----------

function buildFlyPath(roads) {
  if (!roads || roads.length < 4) return null
  const verticals = roads.filter(r => r.depth > r.width)
  const horizontals = roads.filter(r => r.width > r.depth)
  const pts = []
  for (const v of verticals) for (const h of horizontals) pts.push(new THREE.Vector2(v.x, h.z))
  if (pts.length < 3) return null
  const cx = pts.reduce((a, p) => a + p.x, 0) / pts.length
  const cz = pts.reduce((a, p) => a + p.y, 0) / pts.length
  const buckets = new Map()
  for (const p of pts) {
    const ang = Math.atan2(p.y - cz, p.x - cx)
    const bucket = Math.round(ang * 8 / Math.PI)
    const d = (p.x - cx) ** 2 + (p.y - cz) ** 2
    if (!buckets.has(bucket) || buckets.get(bucket).d < d) buckets.set(bucket, { p, d })
  }
  const ordered = [...buckets.entries()].sort((a, b) => a[0] - b[0]).map(e => new THREE.Vector3(e[1].p.x, 6, e[1].p.y))
  if (ordered.length < 3) return null
  return new THREE.CatmullRomCurve3(ordered, true, 'catmullrom', 0.4)
}

// ---------- scene ----------

function CityScene({ city, flythrough, autoRotate, onPickBuilding, selectedId, currentMonth, activeBuildingIds }) {
  const mountRef = useRef(null)
  const stateRef = useRef({})

  useEffect(() => {
    const mount = mountRef.current
    const w = mount.clientWidth
    const h = mount.clientHeight
    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(0xd7e7f7, 0.0028)
    scene.add(makeSkyDome())
    scene.add(makeClouds())
    const camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 3000)
    camera.position.set(110, 75, 110)
    camera.lookAt(0, 6, 0)
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(w, h)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05
    mount.appendChild(renderer.domElement)
    scene.add(new THREE.HemisphereLight(0xbcdcff, 0xd9c89a, 0.9))
    const sun = new THREE.DirectionalLight(0xfff2d8, 1.25)
    sun.position.set(160, 220, 100)
    sun.castShadow = true
    sun.shadow.mapSize.set(2048, 2048)
    sun.shadow.camera.left = -260; sun.shadow.camera.right = 260
    sun.shadow.camera.top = 260; sun.shadow.camera.bottom = -260
    sun.shadow.camera.near = 1; sun.shadow.camera.far = 600
    sun.shadow.bias = -0.0004
    scene.add(sun)
    scene.add(new THREE.DirectionalLight(0xbcdcff, 0.35))
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(1600, 1600),
      new THREE.MeshStandardMaterial({ color: 0x9aa3b0, roughness: 0.95 })
    )
    ground.rotation.x = -Math.PI / 2
    ground.receiveShadow = true
    scene.add(ground)
    const streetGroup = new THREE.Group(); scene.add(streetGroup)
    const buildingsGroup = new THREE.Group(); scene.add(buildingsGroup)
    const highlightGroup = new THREE.Group(); scene.add(highlightGroup)
    const activeGroup = new THREE.Group(); scene.add(activeGroup)

    let frameId, t = 0
    let dragging = false, dragMoved = false
    let lastX = 0, lastY = 0
    let yaw = Math.PI * 0.27
    let pitch = 0.48
    let radius = 180
    const target = new THREE.Vector3(0, 6, 0)

    const onDown = e => {
      if (stateRef.current.flythrough) return
      dragging = true; dragMoved = false
      lastX = e.clientX; lastY = e.clientY
    }
    const onUp = (e) => {
      const wasDrag = dragMoved
      dragging = false
      if (!wasDrag && !stateRef.current.flythrough) tryPick(e)
    }
    const onMove = e => {
      if (!dragging) return
      const dx = e.clientX - lastX
      const dy = e.clientY - lastY
      if (Math.abs(dx) + Math.abs(dy) > 3) dragMoved = true
      yaw -= dx * 0.005
      pitch = Math.max(0.15, Math.min(1.2, pitch - dy * 0.004))
      lastX = e.clientX; lastY = e.clientY
    }
    const onWheel = e => {
      if (stateRef.current.flythrough) return
      radius = Math.max(45, Math.min(420, radius + e.deltaY * 0.15))
    }

    const raycaster = new THREE.Raycaster()
    const ndc = new THREE.Vector2()
    const tryPick = (e) => {
      const rect = renderer.domElement.getBoundingClientRect()
      ndc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      ndc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
      if (ndc.x < -1 || ndc.x > 1 || ndc.y < -1 || ndc.y > 1) return
      raycaster.setFromCamera(ndc, camera)
      const hits = raycaster.intersectObjects(buildingsGroup.children, true)
      for (const h of hits) {
        if (h.object.userData?.building) {
          stateRef.current.onPickBuilding?.(h.object.userData.building)
          return
        }
      }
    }
    renderer.domElement.addEventListener('mousedown', onDown)
    window.addEventListener('mouseup', onUp)
    window.addEventListener('mousemove', onMove)
    renderer.domElement.addEventListener('wheel', onWheel, { passive: true })

    const onResize = () => {
      const nw = mount.clientWidth, nh = mount.clientHeight
      camera.aspect = nw / nh
      camera.updateProjectionMatrix()
      renderer.setSize(nw, nh)
    }
    window.addEventListener('resize', onResize)

    const blinkers = []
    stateRef.current = {
      scene, buildingsGroup, streetGroup, highlightGroup, activeGroup,
      blinkers, renderer, curve: null, flythrough: false, flyU: 0,
      autoRotate: false, onPickBuilding: null,
    }

    const animate = () => {
      t += 0.016
      const s = stateRef.current
      if (s.flythrough && s.curve) {
        s.flyU = (s.flyU + 0.00045) % 1
        const p = s.curve.getPointAt(s.flyU)
        const ahead = s.curve.getPointAt((s.flyU + 0.012) % 1)
        camera.position.set(p.x, p.y + Math.sin(t * 1.2) * 0.4, p.z)
        camera.lookAt(ahead.x, ahead.y - 0.5, ahead.z)
      } else {
        if (s.autoRotate) yaw += 0.0006
        camera.position.set(
          target.x + Math.cos(yaw) * Math.cos(pitch) * radius,
          target.y + Math.sin(pitch) * radius,
          target.z + Math.sin(yaw) * Math.cos(pitch) * radius,
        )
        camera.lookAt(target)
      }
      for (const b of blinkers) {
        b.material.emissiveIntensity = 0.5 + Math.sin(t * 3.4 + b.userData.phase) * 0.8
      }
      for (const obj of highlightGroup.children) {
        if (obj.material) obj.material.opacity = 0.35 + Math.sin(t * 3) * 0.15
      }
      for (const obj of activeGroup.children) {
        if (obj.material) obj.material.opacity = 0.3 + Math.sin(t * 2.5 + (obj.userData.phase || 0)) * 0.2
      }
      renderer.render(scene, camera)
      frameId = requestAnimationFrame(animate)
    }
    animate()

    return () => {
      cancelAnimationFrame(frameId)
      window.removeEventListener('resize', onResize)
      window.removeEventListener('mouseup', onUp)
      window.removeEventListener('mousemove', onMove)
      renderer.dispose()
      mount.removeChild(renderer.domElement)
    }
  }, [])

  useEffect(() => { if (stateRef.current) stateRef.current.flythrough = !!flythrough }, [flythrough])
  useEffect(() => { if (stateRef.current) stateRef.current.autoRotate = !!autoRotate }, [autoRotate])
  useEffect(() => { if (stateRef.current) stateRef.current.onPickBuilding = onPickBuilding }, [onPickBuilding])

  // streets
  useEffect(() => {
    const { streetGroup } = stateRef.current
    if (!streetGroup || !city) return
    while (streetGroup.children.length) {
      const c = streetGroup.children.pop()
      c.geometry?.dispose?.(); c.material?.dispose?.()
    }
    const asphalt = new THREE.MeshStandardMaterial({ color: 0x3a4150, roughness: 0.88 })
    const paint = new THREE.MeshBasicMaterial({ color: 0xf2e7a0 })
    for (const r of city.roads || []) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(r.width, r.depth), asphalt)
      m.rotation.x = -Math.PI / 2
      m.position.set(r.x, 0.02, r.z)
      m.receiveShadow = true
      streetGroup.add(m)
      const long = Math.max(r.width, r.depth)
      const isVertical = r.depth > r.width
      const dashCount = Math.floor(long / 4)
      for (let i = 0; i < dashCount; i++) {
        const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.25, 1.4), paint)
        dash.rotation.x = -Math.PI / 2
        if (isVertical) dash.position.set(r.x, 0.03, r.z - long / 2 + i * 4 + 2)
        else { dash.rotation.z = Math.PI / 2; dash.position.set(r.x - long / 2 + i * 4 + 2, 0.03, r.z) }
        streetGroup.add(dash)
      }
    }
  }, [city])

  // buildings — rebuild on city OR currentMonth change
  useEffect(() => {
    const { buildingsGroup, blinkers } = stateRef.current
    if (!buildingsGroup || !city) return
    while (buildingsGroup.children.length) {
      const c = buildingsGroup.children.pop()
      c.traverse?.(o => {
        o.geometry?.dispose?.()
        if (o.material) {
          if (Array.isArray(o.material)) o.material.forEach(m => m.dispose())
          else o.material.dispose()
        }
      })
    }
    blinkers.length = 0
    for (const b of city.buildings) {
      const h = currentMonth && b.height_by_month ? b.height_by_month[currentMonth] : b.height
      const g = buildBuilding(b, h)
      g.traverse(o => {
        if (o.userData && o.userData.blink) {
          o.userData.phase = Math.random() * Math.PI * 2
          blinkers.push(o)
        }
      })
      buildingsGroup.add(g)
    }
    stateRef.current.curve = buildFlyPath(city.roads)
    stateRef.current.flyU = 0
  }, [city, currentMonth])

  // selection highlight
  useEffect(() => {
    const { highlightGroup } = stateRef.current
    if (!highlightGroup) return
    while (highlightGroup.children.length) {
      const c = highlightGroup.children.pop()
      c.geometry?.dispose?.(); c.material?.dispose?.()
    }
    if (!city || !selectedId) return
    const b = city.buildings.find(x => x.id === selectedId)
    if (!b) return
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(Math.max(b.width, b.depth) * 0.9, Math.max(b.width, b.depth) * 1.15, 32),
      new THREE.MeshBasicMaterial({ color: 0x1d6ed8, transparent: true, opacity: 0.5, side: THREE.DoubleSide })
    )
    ring.rotation.x = -Math.PI / 2
    ring.position.set(b.x, 0.05, b.z)
    highlightGroup.add(ring)
    const beam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.15, 0.15, 200, 8),
      new THREE.MeshBasicMaterial({ color: 0x1d6ed8, transparent: true, opacity: 0.18 })
    )
    beam.position.set(b.x, 100, b.z)
    highlightGroup.add(beam)
  }, [selectedId, city])

  // active-this-month markers
  useEffect(() => {
    const { activeGroup } = stateRef.current
    if (!activeGroup) return
    while (activeGroup.children.length) {
      const c = activeGroup.children.pop()
      c.geometry?.dispose?.(); c.material?.dispose?.()
    }
    if (!city || !activeBuildingIds || activeBuildingIds.size === 0) return
    let phase = 0
    for (const b of city.buildings) {
      if (!activeBuildingIds.has(b.id)) continue
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(Math.max(b.width, b.depth) * 0.7, Math.max(b.width, b.depth) * 0.9, 24),
        new THREE.MeshBasicMaterial({ color: 0x32c862, transparent: true, opacity: 0.45, side: THREE.DoubleSide })
      )
      ring.rotation.x = -Math.PI / 2
      ring.position.set(b.x, 0.04, b.z)
      ring.userData.phase = phase
      phase += 0.4
      activeGroup.add(ring)
    }
  }, [activeBuildingIds, city])

  return <div ref={mountRef} style={{ width: '100%', height: '100%', cursor: 'pointer' }} />
}

// ---------- UI ----------

const styles = {
  root: {
    display: 'grid',
    gridTemplateColumns: '320px 1fr 360px',
    gridTemplateRows: '64px 1fr',
    height: '100vh',
    background: '#eef2f8',
    color: '#1a2238',
    fontFamily: 'ui-sans-serif, -apple-system, "SF Pro Display", "Inter", system-ui, sans-serif',
  },
  header: {
    gridColumn: '1 / 4',
    display: 'flex', alignItems: 'center', gap: 18, padding: '0 24px',
    background: 'linear-gradient(180deg, #ffffff, #f3f6fb)',
    borderBottom: '1px solid #d8dee8',
    boxShadow: '0 2px 10px rgba(20,40,80,0.04)',
  },
  logoDot: {
    width: 12, height: 12, borderRadius: 999,
    background: 'radial-gradient(circle, #4fb0ff 0%, #1d6ed8 80%)',
    boxShadow: '0 0 14px rgba(40,140,255,0.6)',
  },
  title: { margin: 0, fontSize: 17, letterSpacing: 1.4, textTransform: 'uppercase', fontWeight: 700, color: '#13213d' },
  titleAccent: { color: '#1d6ed8' },
  chip: {
    padding: '5px 10px', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase',
    color: '#4a5a78', border: '1px solid #c5d1e2', borderRadius: 999, background: '#f6f9fd',
  },
  hint: { marginLeft: 'auto', fontSize: 12, color: '#6a7a96', letterSpacing: 0.4 },
  sidebar: { padding: '20px 18px', background: '#ffffff', borderRight: '1px solid #d8dee8', overflowY: 'auto' },
  rightPanel: { padding: '20px 18px', background: '#ffffff', borderLeft: '1px solid #d8dee8', overflowY: 'auto' },
  sectionTitle: { fontSize: 10, letterSpacing: 2, textTransform: 'uppercase', color: '#6a7a96', margin: '0 0 10px 0' },
  card: {
    padding: 14, border: '1px solid #dde4ee', borderRadius: 12,
    background: '#fbfcfe', marginBottom: 14, boxShadow: '0 1px 2px rgba(20,40,80,0.03)',
  },
  statRow: { display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '4px 0' },
  statKey: { color: '#6a7a96' },
  statVal: { color: '#13213d', fontVariantNumeric: 'tabular-nums', fontWeight: 600 },
  legendRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '3px 0', fontSize: 12, color: '#3a4862' },
  legendSwatch: { width: 12, height: 12, borderRadius: 3, boxShadow: '0 1px 2px rgba(0,0,0,0.18)' },
  main: { position: 'relative' },
  toggleBtn: (active) => ({
    padding: '8px 12px', borderRadius: 8,
    border: `1px solid ${active ? '#1d6ed8' : '#c5d1e2'}`,
    background: active ? '#1d6ed8' : '#ffffff',
    color: active ? '#ffffff' : '#1d6ed8',
    fontSize: 12, letterSpacing: 0.8, fontWeight: 700, cursor: 'pointer', textTransform: 'uppercase',
  }),
  input: {
    width: '100%', padding: '9px 10px', fontSize: 13,
    border: '1px solid #c5d1e2', borderRadius: 8, background: '#ffffff',
    color: '#13213d', boxSizing: 'border-box',
  },
  primaryBtn: {
    marginTop: 8, width: '100%', padding: '10px 12px',
    background: '#1d6ed8', color: '#fff', border: 'none', borderRadius: 8,
    fontSize: 13, fontWeight: 700, letterSpacing: 0.6, cursor: 'pointer', textTransform: 'uppercase',
  },
  hud: {
    position: 'absolute', left: 20, bottom: 20, right: 20,
    padding: '14px 16px',
    border: '1px solid #d8dee8',
    borderRadius: 14,
    background: 'rgba(255,255,255,0.92)',
    backdropFilter: 'blur(12px)',
    boxShadow: '0 8px 32px rgba(20,40,80,0.12)',
  },
  monthLabel: { fontSize: 11, color: '#6a7a96', letterSpacing: 0.8, marginBottom: 6, textTransform: 'uppercase' },
  monthHeader: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 },
  monthCurrent: { fontSize: 22, fontWeight: 700, color: '#13213d', fontVariantNumeric: 'tabular-nums' },
  monthCount: { fontSize: 14, color: '#1d6ed8', fontWeight: 700 },
  barRow: { display: 'flex', alignItems: 'flex-end', gap: 4, height: 56, marginTop: 6 },
  bar: (h, active, hovered) => ({
    flex: 1, height: `${Math.max(4, h * 56)}%`,
    background: active ? '#1d6ed8' : hovered ? '#5e9fe6' : '#bcd0ec',
    borderRadius: 3, cursor: 'pointer',
    transition: 'background 0.15s',
  }),
  monthTicks: { display: 'flex', gap: 4, marginTop: 6, fontSize: 9, color: '#8a96b3' },
  monthTick: { flex: 1, textAlign: 'center', fontVariantNumeric: 'tabular-nums' },
}

const LANG_SWATCH = {
  Python: '#4f8cd9', JavaScript: '#f0db4f', TypeScript: '#2f74c0', Go: '#00add8',
  Rust: '#d9533a', Java: '#b87921', 'C++': '#ed4063', 'C#': '#558b55',
  Ruby: '#cc342d', PHP: '#4f5b93', Swift: '#f58220', Kotlin: '#a965d1',
  Shell: '#89e051', HTML: '#e54b3b', CSS: '#5c8bd9', Vue: '#42b883',
  Dart: '#00b4ab', Scala: '#c95252',
}

function RepoCard({ repo, currentMonth, monthlyCommits }) {
  if (!repo) return (
    <div style={{ fontSize: 13, color: '#6a7a96', padding: 12 }}>
      Click any building to see repo details.
    </div>
  )
  const lang = repo.language
  const langColor = LANG_SWATCH[lang] || '#9aa3b0'
  return (
    <div>
      <div style={{ ...styles.card, padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
          <span style={{ width: 10, height: 10, borderRadius: 999, background: langColor, boxShadow: `0 0 8px ${langColor}` }} />
          <span style={{ fontSize: 12, color: '#6a7a96', letterSpacing: 0.4 }}>{lang || 'unknown'}</span>
          {repo.archived && <span style={{ ...styles.chip, color: '#a3724a', borderColor: '#e8c39a', background: '#fff5e8' }}>archived</span>}
          {repo.fork && <span style={{ ...styles.chip, color: '#5c7aa3' }}>fork</span>}
        </div>
        <div style={{ fontSize: 19, fontWeight: 700, color: '#13213d', wordBreak: 'break-word' }}>{repo.name}</div>
        <div style={{ fontSize: 12, color: '#6a7a96', marginTop: 2 }}>{repo.full_name}</div>
        {repo.url && (
          <a href={repo.url} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: '#1d6ed8', textDecoration: 'none', display: 'inline-block', marginTop: 8 }}>
            github.com ↗
          </a>
        )}
      </div>

      <div style={styles.card}>
        <p style={styles.sectionTitle}>Summary</p>
        <div style={{ fontSize: 13, lineHeight: 1.55, color: '#2a3550' }}>
          {(repo.summary || []).map((l, i) => <div key={i} style={{ marginBottom: 4 }}>{l}</div>)}
        </div>
      </div>

      <div style={styles.card}>
        <p style={styles.sectionTitle}>Stats</p>
        <div style={styles.statRow}><span style={styles.statKey}>total commits</span><span style={styles.statVal}>{repo.commit_count}</span></div>
        {currentMonth && monthlyCommits && (
          <div style={styles.statRow}><span style={styles.statKey}>commits in {currentMonth}</span><span style={styles.statVal}>{monthlyCommits[currentMonth] ?? 0}</span></div>
        )}
        <div style={styles.statRow}><span style={styles.statKey}>stars</span><span style={styles.statVal}>{repo.stars}</span></div>
        <div style={styles.statRow}><span style={styles.statKey}>forks</span><span style={styles.statVal}>{repo.forks}</span></div>
        <div style={styles.statRow}><span style={styles.statKey}>open issues</span><span style={styles.statVal}>{repo.open_issues}</span></div>
        <div style={styles.statRow}><span style={styles.statKey}>default branch</span><span style={styles.statVal}>{repo.default_branch}</span></div>
        <div style={styles.statRow}><span style={styles.statKey}>created</span><span style={styles.statVal}>{(repo.created_at || '').slice(0, 10)}</span></div>
        <div style={styles.statRow}><span style={styles.statKey}>pushed</span><span style={styles.statVal}>{(repo.pushed_at || '').slice(0, 10)}</span></div>
      </div>

      {repo.last_commit?.sha && (
        <div style={styles.card}>
          <p style={styles.sectionTitle}>Last Commit</p>
          <div style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12, color: '#1d6ed8' }}>{repo.last_commit.sha}</div>
          <div style={{ fontSize: 13, color: '#13213d', marginTop: 4 }}>{repo.last_commit.message}</div>
          <div style={{ fontSize: 12, color: '#6a7a96', marginTop: 4 }}>{repo.last_commit.author} · {(repo.last_commit.date || '').slice(0, 16).replace('T', ' ')}</div>
        </div>
      )}

      {(repo.topics || []).length > 0 && (
        <div style={styles.card}>
          <p style={styles.sectionTitle}>Topics</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {repo.topics.map(t => <span key={t} style={styles.chip}>{t}</span>)}
          </div>
        </div>
      )}
    </div>
  )
}

function MonthLabel(s) {
  const [y, m] = s.split('-')
  const names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${names[parseInt(m) - 1]} ${y.slice(2)}`
}

export default function App() {
  const [city, setCity] = useState(null)
  const [loadState, setLoadState] = useState({ state: 'idle' })
  const [userInput, setUserInput] = useState('')
  const [tokenInput, setTokenInput] = useState(() => localStorage.getItem('gh_token') || '')
  const [flythrough, setFlythrough] = useState(false)
  const [autoRotate, setAutoRotate] = useState(false)
  const [selectedBuilding, setSelectedBuilding] = useState(null)
  const [monthIdx, setMonthIdx] = useState(null) // null = final / latest
  const [playing, setPlaying] = useState(false)

  const months = city?.months || []
  const currentMonth = monthIdx != null && months.length ? months[monthIdx] : null

  const submitProfile = async () => {
    const u = userInput.trim().replace(/^@/, '')
    if (!u) return
    setLoadState({ state: 'running' })
    setSelectedBuilding(null)
    setCity(null)
    const token = tokenInput.trim()
    if (token) localStorage.setItem('gh_token', token)
    try {
      const res = await fetch(`${API}/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: u, token: token || undefined }),
      })
      const data = await res.json()
      if (!res.ok) { setLoadState({ state: 'error', error: data.error || 'fetch failed' }); return }
      setLoadState({ state: 'done', user: data.user, repos: data.repos, commits: data.total_commits, windowCommits: data.window_commits, rate: data.rate_limit })
      const c = await fetch(`${API}/city?user=${encodeURIComponent(u)}`).then(r => r.json())
      setCity(c)
      setMonthIdx(c.months ? c.months.length - 1 : null)
    } catch (e) {
      setLoadState({ state: 'error', error: String(e) })
    }
  }

  // auto play
  useEffect(() => {
    if (!playing || !months.length) return
    const id = setInterval(() => {
      setMonthIdx(i => (i == null ? 0 : (i >= months.length - 1 ? 0 : i + 1)))
    }, 900)
    return () => clearInterval(id)
  }, [playing, months.length])

  const monthlyBars = useMemo(() => {
    if (!city?.profile_monthly || !months.length) return []
    const max = Math.max(1, ...Object.values(city.profile_monthly))
    return months.map(m => ({ month: m, count: city.profile_monthly[m] || 0, h: (city.profile_monthly[m] || 0) / max }))
  }, [city, months])

  const activeBuildingIds = useMemo(() => {
    if (!city || !currentMonth) return new Set()
    const set = new Set()
    for (const b of city.buildings) {
      if (b.monthly_commits && b.monthly_commits[currentMonth] > 0) set.add(b.id)
    }
    return set
  }, [city, currentMonth])

  const langSummary = useMemo(() => {
    if (!city?.buildings) return []
    const counts = {}
    for (const b of city.buildings) {
      const k = b.neighborhood || 'other'
      counts[k] = (counts[k] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 12)
  }, [city])

  const selectedRepo = selectedBuilding?.repo

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <div style={styles.logoDot} />
        <h1 style={styles.title}>The <span style={styles.titleAccent}>Time</span> Machine</h1>
        {city ? (
          <>
            <span style={styles.chip}>@{city.user?.login}</span>
            <span style={styles.chip}>{city.buildings.length} repos</span>
            <span style={styles.chip}>{city.stats.total_commits} commits</span>
            <span style={styles.chip}>{city.stats.window_commits} in last 12mo</span>
          </>
        ) : (
          <span style={styles.chip}>no profile loaded</span>
        )}
        <span style={styles.hint}>click building · drag to orbit · scroll to zoom</span>
      </header>

      <aside style={styles.sidebar}>
        <div style={styles.card}>
          <p style={styles.sectionTitle}>GitHub Profile</p>
          <input
            style={styles.input}
            placeholder="username (e.g. torvalds)"
            value={userInput}
            onChange={e => setUserInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') submitProfile() }}
            disabled={loadState.state === 'running'}
          />
          <input
            type="password"
            style={{ ...styles.input, marginTop: 6 }}
            placeholder="GitHub token (optional, raises rate limit)"
            value={tokenInput}
            onChange={e => setTokenInput(e.target.value)}
            disabled={loadState.state === 'running'}
          />
          <button style={styles.primaryBtn} onClick={submitProfile} disabled={loadState.state === 'running'}>
            {loadState.state === 'running' ? 'Building…' : 'Build City'}
          </button>
          {loadState.state === 'done' && (
            <div style={{ fontSize: 12, color: '#3a7a3a', marginTop: 8 }}>
              ✓ {loadState.user} — {loadState.repos} repos, {loadState.commits} commits
              {loadState.rate && <div style={{ fontSize: 11, color: '#6a7a96', marginTop: 2 }}>rate limit: {loadState.rate.remaining}/{loadState.rate.limit}</div>}
            </div>
          )}
          {loadState.state === 'error' && (
            <div style={{ fontSize: 12, color: '#cc3333', marginTop: 8 }}>✗ {loadState.error}</div>
          )}
          <div style={{ fontSize: 11, color: '#6a7a96', marginTop: 6, lineHeight: 1.4 }}>
            Tip: unauth = 60 req/hr. <a href="https://github.com/settings/tokens?type=beta" target="_blank" rel="noreferrer" style={{ color: '#1d6ed8' }}>Get a token</a> (no scopes needed for public repos) for 5000/hr.
          </div>
        </div>

        {city?.user && (
          <div style={styles.card}>
            <p style={styles.sectionTitle}>User</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {city.user.avatar_url && (
                <img src={city.user.avatar_url} alt="" style={{ width: 44, height: 44, borderRadius: 999, border: '1px solid #d8dee8' }} />
              )}
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 700, color: '#13213d', overflow: 'hidden', textOverflow: 'ellipsis' }}>{city.user.name}</div>
                <div style={{ fontSize: 12, color: '#6a7a96' }}>@{city.user.login}</div>
              </div>
            </div>
            {city.user.bio && <div style={{ fontSize: 13, color: '#3a4862', marginTop: 8 }}>{city.user.bio}</div>}
            <div style={{ display: 'flex', gap: 14, fontSize: 12, color: '#6a7a96', marginTop: 8 }}>
              <span><b style={{ color: '#13213d' }}>{city.user.public_repos}</b> repos</span>
              <span><b style={{ color: '#13213d' }}>{city.user.followers}</b> followers</span>
              <span><b style={{ color: '#13213d' }}>{city.user.following}</b> following</span>
            </div>
          </div>
        )}

        {city && (
          <div style={styles.card}>
            <p style={styles.sectionTitle}>Camera</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button style={styles.toggleBtn(flythrough)} onClick={() => setFlythrough(f => !f)}>
                {flythrough ? '■ stop flythrough' : '▶ flythrough streets'}
              </button>
              <button style={styles.toggleBtn(autoRotate)} onClick={() => setAutoRotate(a => !a)}>
                {autoRotate ? '■ auto-rotate on' : '○ auto-rotate off'}
              </button>
            </div>
          </div>
        )}

        {city && (
          <div style={styles.card}>
            <p style={styles.sectionTitle}>Legend</p>
            <div style={{ fontSize: 12, color: '#3a4862', lineHeight: 1.6 }}>
              <div>1 building = 1 repo</div>
              <div>height = cumulative commits at selected month</div>
              <div>footprint = stars</div>
              <div>color = primary language</div>
              <div>green ring = active that month</div>
              <div>gray = archived</div>
            </div>
          </div>
        )}

        {langSummary.length > 0 && (
          <div style={styles.card}>
            <p style={styles.sectionTitle}>Languages</p>
            {langSummary.map(([n, count]) => (
              <div key={n} style={styles.legendRow}>
                <span style={{ ...styles.legendSwatch, background: LANG_SWATCH[n] || '#9aa3b0' }} />
                <span style={{ flex: 1 }}>{n}</span>
                <span style={{ color: '#6a7a96', fontSize: 11 }}>{count}</span>
              </div>
            ))}
          </div>
        )}
      </aside>

      <main style={styles.main}>
        {city ? (
          <>
            <CityScene
              city={city}
              flythrough={flythrough}
              autoRotate={autoRotate}
              selectedId={selectedBuilding?.id}
              onPickBuilding={setSelectedBuilding}
              currentMonth={currentMonth}
              activeBuildingIds={activeBuildingIds}
            />
            {monthlyBars.length > 0 && (
              <div style={styles.hud}>
                <div style={styles.monthHeader}>
                  <div>
                    <div style={styles.monthLabel}>Month</div>
                    <div style={styles.monthCurrent}>{currentMonth ? MonthLabel(currentMonth) : '—'}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={styles.monthLabel}>Commits</div>
                    <div style={styles.monthCount}>{currentMonth ? city.profile_monthly[currentMonth] || 0 : 0}</div>
                  </div>
                  <button
                    onClick={() => setPlaying(p => !p)}
                    style={{
                      width: 38, height: 38, borderRadius: 999, border: '1px solid #c5d1e2',
                      background: '#ffffff', color: '#1d6ed8', fontSize: 14, fontWeight: 700, cursor: 'pointer',
                    }}
                  >{playing ? '❚❚' : '▶'}</button>
                </div>
                <div style={styles.barRow}>
                  {monthlyBars.map((b, i) => (
                    <div
                      key={b.month}
                      onClick={() => { setMonthIdx(i); setPlaying(false) }}
                      title={`${MonthLabel(b.month)} · ${b.count} commits`}
                      style={styles.bar(b.h, i === monthIdx, false)}
                    />
                  ))}
                </div>
                <div style={styles.monthTicks}>
                  {monthlyBars.map(b => (
                    <span key={b.month} style={styles.monthTick}>{MonthLabel(b.month).split(' ')[0]}</span>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div style={{ padding: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#13213d', letterSpacing: 0.5 }}>Enter a GitHub username</div>
            <div style={{ fontSize: 14, color: '#6a7a96', maxWidth: 420, textAlign: 'center', lineHeight: 1.5 }}>
              Each repo becomes a building. Height = commits. Scrub the monthly timeline to watch the skyline grow.
            </div>
          </div>
        )}
      </main>

      <aside style={styles.rightPanel}>
        <p style={styles.sectionTitle}>Inspector</p>
        <RepoCard
          repo={selectedRepo}
          currentMonth={currentMonth}
          monthlyCommits={selectedBuilding?.monthly_commits}
        />
      </aside>
    </div>
  )
}
