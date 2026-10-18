import { useEffect, useRef } from "react";
import * as THREE from "three";

// Offices a HolidayOps customer might span: [latitude, longitude].
const CITIES: [number, number][] = [
  [24.86, 67.0], // Karachi
  [24.71, 46.68], // Riyadh
  [25.2, 55.27], // Dubai
  [51.5, -0.12], // London
  [40.71, -74.0], // New York
  [-1.29, 36.82], // Nairobi
  [1.35, 103.82], // Singapore
  [35.68, 139.69], // Tokyo
  [-23.55, -46.63], // Sao Paulo
  [41.01, 28.98], // Istanbul
];
const ROUTES: [number, number][] = [
  [0, 1],
  [0, 3],
  [1, 2],
  [2, 6],
  [3, 4],
  [4, 8],
  [5, 2],
  [6, 7],
  [9, 3],
  [0, 7],
];
const TEAL = new THREE.Color("#2dd4c4");
const GLOW = new THREE.Color("#00d1c1");
const DOTS = new THREE.Color("#e6edf7");
const RADIUS = 1;
const ARC_POINTS = 64;

function toVector(lat: number, lon: number, radius = RADIUS): THREE.Vector3 {
  const phi = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lon + 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

// Evenly spread points on a sphere (Fibonacci lattice): reads as a dotted globe without a texture.
function sphereDots(count: number): Float32Array {
  const positions = new Float32Array(count * 3);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    positions.set([Math.cos(golden * i) * r, y, Math.sin(golden * i) * r], i * 3);
  }
  return positions;
}

function arc(from: THREE.Vector3, to: THREE.Vector3): THREE.QuadraticBezierCurve3 {
  const lift = 1 + from.distanceTo(to) * 0.45;
  const middle = from.clone().add(to).multiplyScalar(0.5).normalize().multiplyScalar(lift);
  return new THREE.QuadraticBezierCurve3(from, middle, to);
}

/** Decorative WebGL globe for the auth pages: dotted Earth, offices, flight routes drawing
 * between them. One still frame under prefers-reduced-motion; paused when off screen. */
export function GlobeArt({ className }: { className?: string }) {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      return; // No WebGL: the panel's gradient and copy stand on their own.
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.setAttribute("aria-hidden", "true");
    element.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 0, 4.2);
    const globe = new THREE.Group();
    // Low and to the reading end: the headline keeps the top, the globe rises from the corner.
    globe.position.set(0.45, -0.42, 0);
    globe.scale.setScalar(1.05);
    globe.rotation.set(0.35, -1.2, 0);
    scene.add(globe);

    const disposables: { dispose: () => void }[] = [];
    const keep = <T extends { dispose: () => void }>(item: T): T => {
      disposables.push(item);
      return item;
    };

    const dotGeometry = keep(new THREE.BufferGeometry());
    dotGeometry.setAttribute("position", new THREE.BufferAttribute(sphereDots(2200), 3));
    globe.add(
      new THREE.Points(
        dotGeometry,
        keep(
          new THREE.PointsMaterial({
            color: DOTS,
            size: 0.012,
            transparent: true,
            opacity: 0.45,
            depthWrite: false,
          }),
        ),
      ),
    );

    // A dark core hides the far side's dots, so the globe reads as solid.
    globe.add(
      new THREE.Mesh(
        keep(new THREE.SphereGeometry(RADIUS * 0.985, 48, 48)),
        keep(new THREE.MeshBasicMaterial({ color: "#081430", transparent: true, opacity: 0.9 })),
      ),
    );

    // Fresnel rim: glows only where the surface turns away from the camera, like an atmosphere.
    globe.add(
      new THREE.Mesh(
        keep(new THREE.SphereGeometry(RADIUS * 1.04, 48, 48)),
        keep(
          new THREE.ShaderMaterial({
            uniforms: { glow: { value: GLOW } },
            vertexShader: `varying vec3 vNormal; varying vec3 vView;
              void main() {
                vec4 world = modelViewMatrix * vec4(position, 1.0);
                vNormal = normalize(normalMatrix * normal);
                vView = normalize(-world.xyz);
                gl_Position = projectionMatrix * world;
              }`,
            fragmentShader: `uniform vec3 glow; varying vec3 vNormal; varying vec3 vView;
              void main() {
                float rim = pow(1.0 - max(dot(vNormal, vView), 0.0), 3.0);
                gl_FragColor = vec4(glow, rim * 0.9);
              }`,
            blending: THREE.AdditiveBlending,
            transparent: true,
            depthWrite: false,
          }),
        ),
      ),
    );

    const cityPoints = CITIES.map(([lat, lon]) => toVector(lat, lon, RADIUS * 1.005));
    const markerGeometry = keep(new THREE.SphereGeometry(0.018, 12, 12));
    const markerMaterial = keep(new THREE.MeshBasicMaterial({ color: TEAL }));
    const ringGeometry = keep(new THREE.RingGeometry(0.03, 0.04, 32));
    const rings: THREE.Mesh<THREE.RingGeometry, THREE.MeshBasicMaterial>[] = [];
    for (const point of cityPoints) {
      const marker = new THREE.Mesh(markerGeometry, markerMaterial);
      marker.position.copy(point);
      globe.add(marker);
      const ring = new THREE.Mesh(
        ringGeometry,
        keep(
          new THREE.MeshBasicMaterial({
            color: GLOW,
            transparent: true,
            side: THREE.DoubleSide,
            depthWrite: false,
          }),
        ),
      );
      ring.position.copy(point);
      ring.lookAt(point.clone().multiplyScalar(2));
      globe.add(ring);
      rings.push(ring);
    }

    const planeGeometry = keep(new THREE.SphereGeometry(0.014, 8, 8));
    const planeMaterial = keep(new THREE.MeshBasicMaterial({ color: 0xffffff }));
    const flights = ROUTES.flatMap(([a, b], index) => {
      const from = cityPoints[a];
      const to = cityPoints[b];
      if (!from || !to) return [];
      const curve = arc(from, to);
      const geometry = keep(new THREE.BufferGeometry().setFromPoints(curve.getPoints(ARC_POINTS)));
      const line = new THREE.Line(
        geometry,
        keep(new THREE.LineBasicMaterial({ color: TEAL, transparent: true, opacity: 0.85 })),
      );
      const plane = new THREE.Mesh(planeGeometry, planeMaterial);
      globe.add(line, plane);
      return [{ curve, geometry, line, plane, offset: index / ROUTES.length }];
    });

    const resize = () => {
      const { width, height } = element.getBoundingClientRect();
      if (!width || !height) return;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();

    const pointer = { x: 0, y: 0 };
    const onPointer = (event: PointerEvent) => {
      const box = element.getBoundingClientRect();
      pointer.x = ((event.clientX - box.left) / box.width - 0.5) * 2;
      pointer.y = ((event.clientY - box.top) / box.height - 0.5) * 2;
    };
    element.addEventListener("pointermove", onPointer);

    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const clock = new THREE.Clock();
    const draw = (time: number) => {
      globe.rotation.y = -1.2 + time * 0.08 + pointer.x * 0.15;
      globe.rotation.x = 0.35 + pointer.y * 0.08;
      for (const flight of flights) {
        // Each route draws in, carries its plane across, then fades before the next lap.
        const t = (time * 0.12 + flight.offset) % 1;
        const drawn = Math.min(1, t * 2);
        flight.geometry.setDrawRange(0, Math.max(2, Math.floor(drawn * (ARC_POINTS + 1))));
        (flight.line.material as THREE.LineBasicMaterial).opacity =
          t > 0.85 ? (1 - t) / 0.15 : 0.85;
        flight.plane.visible = t < 0.85;
        flight.plane.position.copy(flight.curve.getPoint(Math.min(drawn, 1)));
      }
      rings.forEach((ring, i) => {
        const pulse = (time * 0.5 + i / rings.length) % 1;
        ring.scale.setScalar(1 + pulse * 2.5);
        ring.material.opacity = 0.7 * (1 - pulse);
      });
      renderer.render(scene, camera);
    };

    let frame = 0;
    let visible = true;
    const loop = () => {
      frame = requestAnimationFrame(loop);
      if (visible && !document.hidden) draw(clock.getElapsedTime());
    };
    const visibility = new IntersectionObserver(([entry]) => {
      visible = entry?.isIntersecting ?? true;
    });
    visibility.observe(element);
    if (still) draw(4);
    else loop();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      visibility.disconnect();
      element.removeEventListener("pointermove", onPointer);
      disposables.forEach((item) => item.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return <div ref={host} className={className} />;
}
