import * as THREE from 'three';

export function geographicVector(lat, lon) {
  const latitude = THREE.MathUtils.degToRad(lat);
  const longitude = THREE.MathUtils.degToRad(lon);
  return new THREE.Vector3(Math.cos(latitude) * Math.cos(longitude), Math.sin(latitude), -Math.cos(latitude) * Math.sin(longitude));
}

function facingQuaternion(lat, lon) {
  return new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), THREE.MathUtils.degToRad(lat))
    .multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -Math.PI / 2 - THREE.MathUtils.degToRad(lon)));
}

export function createEarthScene(host, { onFailure, initialPlace = null, paused = false }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.setAttribute('aria-hidden', 'true');
  host.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(43, 1, 0.1, 50);
  camera.position.z = 3.4;
  const globe = new THREE.Group();
  globe.quaternion.copy(facingQuaternion(18, 76));
  scene.add(globe);
  let disposed = false;
  let stopped = paused;
  let interactionFocused = false;
  let visible = true;
  let focused = null;
  let transition = false;
  let previousTime = 0;
  let targetDistance = 3.4;
  const targetQuaternion = globe.quaternion.clone();
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  let reduced = media.matches;
  const resources = new Set();
  const own = value => { resources.add(value); return value; };
  const earthMaterial = own(new THREE.MeshPhongMaterial({ color: 0xffffff, shininess: 8, specular: 0x183d5e, emissive: 0x091c35, emissiveIntensity: 0.25 }));
  globe.add(new THREE.Mesh(own(new THREE.SphereGeometry(1, 80, 64)), earthMaterial));
  const texture = own(new THREE.TextureLoader().load('/earth/blue-marble.jpg', loaded => {
    if (disposed) { loaded.dispose(); return; }
    loaded.colorSpace = THREE.SRGBColorSpace;
    loaded.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
    earthMaterial.map = loaded;
    earthMaterial.needsUpdate = true;
    host.dataset.texture = 'ready';
    render();
  }, undefined, () => { if (!disposed) onFailure('The Earth texture could not load. Place search still works.'); }));
  texture.colorSpace = THREE.SRGBColorSpace;
  scene.add(new THREE.AmbientLight(0xd9edff, 1.65));
  const sun = new THREE.DirectionalLight(0xe1f0ff, 2.2);
  sun.position.set(-3, 3, 5);
  scene.add(sun);

  const clouds = new THREE.Mesh(own(new THREE.SphereGeometry(1.014, 64, 40)), own(new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    vertexShader: 'varying vec3 vPoint; void main(){vPoint=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: `varying vec3 vPoint;
      float hash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
      float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
        return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
        mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
      void main(){vec3 p=normalize(vPoint)*8.0; float n=noise(p)*0.58+noise(p*2.1)*0.28+noise(p*4.2)*0.14;
        float alpha=smoothstep(0.49,0.73,n)*0.29;gl_FragColor=vec4(0.87,0.95,1.0,alpha);}`,
  })));
  globe.add(clouds);

  const atmosphere = new THREE.Mesh(own(new THREE.SphereGeometry(1.045, 64, 40)), own(new THREE.ShaderMaterial({
    side: THREE.BackSide, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: 'varying vec3 vNormal;varying vec3 vView;void main(){vec4 p=modelViewMatrix*vec4(position,1.0);vNormal=normalize(normalMatrix*normal);vView=normalize(-p.xyz);gl_Position=projectionMatrix*p;}',
    fragmentShader: 'varying vec3 vNormal;varying vec3 vView;void main(){float rim=pow(max(0.0,1.0-abs(dot(normalize(vNormal),normalize(vView)))),3.0);gl_FragColor=vec4(0.14,0.58,1.0,rim*0.65);}',
  })));
  globe.add(atmosphere);
  const marker = new THREE.Group();
  marker.add(new THREE.Mesh(own(new THREE.SphereGeometry(0.016, 16, 12)), own(new THREE.MeshBasicMaterial({ color: 0x75ffe2 }))));
  const ring = new THREE.Mesh(own(new THREE.RingGeometry(0.029, 0.035, 48)), own(new THREE.MeshBasicMaterial({ color: 0x75ffe2, transparent: true, opacity: 0.8, side: THREE.DoubleSide })));
  marker.add(ring);
  marker.visible = false;
  globe.add(marker);

  const stars = [];
  for (let i = 0; i < 320; i++) {
    const angle = i * 2.399963;
    const z = 1 - 2 * ((i + 0.5) / 320);
    const radius = Math.sqrt(1 - z * z);
    stars.push(Math.cos(angle) * radius * 18, Math.sin(angle) * radius * 18, z * 18);
  }
  const starGeometry = own(new THREE.BufferGeometry());
  starGeometry.setAttribute('position', new THREE.Float32BufferAttribute(stars, 3));
  scene.add(new THREE.Points(starGeometry, own(new THREE.PointsMaterial({ color: 0x90bedc, size: 0.035, transparent: true, opacity: 0.55 }))));

  function render() {
    if (disposed || !visible || document.hidden) return;
    renderer.render(scene, camera);
    host.dataset.cameraDistance = camera.position.z.toFixed(3);
    const centre = new THREE.Vector3(0, 0, 1).applyQuaternion(globe.quaternion.clone().invert());
    host.dataset.centerLatitude = THREE.MathUtils.radToDeg(Math.asin(centre.y)).toFixed(5);
    host.dataset.centerLongitude = THREE.MathUtils.radToDeg(Math.atan2(-centre.z, centre.x)).toFixed(5);
    if (focused) {
      const point = geographicVector(focused.lat, focused.lon).applyQuaternion(globe.quaternion);
      host.dataset.focusError = point.distanceTo(new THREE.Vector3(0, 0, 1)).toFixed(5);
    }
  }
  function animate(time) {
    const dt = previousTime ? Math.min((time - previousTime) / 1000, 0.05) : 0;
    previousTime = time;
    if (transition) {
      const alpha = 1 - Math.exp(-dt * 4.5);
      globe.quaternion.slerp(targetQuaternion, alpha);
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, targetDistance, alpha);
      if (globe.quaternion.angleTo(targetQuaternion) < 0.001 && Math.abs(camera.position.z - targetDistance) < 0.001) {
        globe.quaternion.copy(targetQuaternion); camera.position.z = targetDistance; transition = false;
        host.dataset.focusState = focused ? 'settled' : 'orbit';
      }
    } else if (!focused && !stopped && !reduced && !interactionFocused) {
      globe.rotateY(dt * 0.025);
      targetQuaternion.copy(globe.quaternion);
    }
    if (!stopped && !reduced && !interactionFocused) clouds.rotateY(dt * 0.012);
    render();
    if (!transition && (stopped || reduced || interactionFocused)) syncLoop();
  }
  function syncLoop() {
    if (disposed) return;
    const active = visible && !document.hidden;
    if (reduced || stopped) {
      if (transition) { globe.quaternion.copy(targetQuaternion); camera.position.z = targetDistance; transition = false; }
      host.dataset.focusState = focused ? 'settled' : 'orbit';
    }
    host.dataset.motion = !active ? 'suspended' : reduced ? 'reduced' : stopped ? 'paused' : interactionFocused ? 'interaction-paused' : 'running';
    previousTime = 0;
    renderer.setAnimationLoop(active && (!stopped && !reduced && !interactionFocused || transition) ? animate : null);
    render();
  }
  function focus(place) {
    focused = place;
    targetQuaternion.copy(facingQuaternion(place ? place.lat : 18, place ? place.lon : 76));
    targetDistance = place ? 2.7 : 3.4;
    marker.visible = Boolean(place);
    if (place) {
      const point = geographicVector(place.lat, place.lon);
      marker.position.copy(point).multiplyScalar(1.028);
      marker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), point);
    }
    host.dataset.focusLat = place ? String(place.lat) : '';
    host.dataset.focusLon = place ? String(place.lon) : '';
    host.dataset.focusState = 'moving';
    transition = true;
    syncLoop();
  }
  function resize() {
    if (disposed) return;
    const width = Math.max(1, host.clientWidth), height = Math.max(1, host.clientHeight);
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    render();
  }
  function mediaChange(event) { reduced = event.matches; syncLoop(); }
  function contextLost(event) { event.preventDefault(); if (!disposed) onFailure('3D rendering was interrupted. Place search still works.'); }
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  const intersection = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; syncLoop(); }, { threshold: 0.02 });
  intersection.observe(host);
  media.addEventListener('change', mediaChange);
  document.addEventListener('visibilitychange', syncLoop);
  renderer.domElement.addEventListener('webglcontextlost', contextLost);
  host.dataset.renderState = 'ready';
  resize();
  focus(initialPlace);
  return {
    focus,
    pause(value) { stopped = value; syncLoop(); },
    interaction(value) { interactionFocused = value; syncLoop(); },
    rotate(direction) {
      focused = null;
      marker.visible = false;
      host.dataset.focusLat = ''; host.dataset.focusLon = ''; host.dataset.focusState = 'moving';
      targetQuaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), direction * Math.PI / 8));
      transition = true; syncLoop();
    },
    dispose() {
      disposed = true;
      renderer.setAnimationLoop(null);
      resizeObserver.disconnect(); intersection.disconnect();
      media.removeEventListener('change', mediaChange);
      document.removeEventListener('visibilitychange', syncLoop);
      renderer.domElement.removeEventListener('webglcontextlost', contextLost);
      for (const resource of resources) resource.dispose();
      scene.clear(); renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
    },
  };
}
