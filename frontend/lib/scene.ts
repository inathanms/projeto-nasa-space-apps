type Vec = [number, number, number];
type Point = { x: number; y: number; depth: number };
type Raster = { pixels: ImageData; radius: number; longitude: Float32Array; latitude: Float32Array; light: Float32Array };

const rad = Math.PI / 180;
const tau = 2 * Math.PI;
const turn = (angle: number) => ((angle % 1) + 1) % 1;
const dot = ([x, y, z]: Vec, [a, b, c]: Vec) => x * a + y * b + z * c;
const add = ([x, y, z]: Vec, [a, b, c]: Vec): Vec => [x + a, y + b, z + c];
const scale = ([x, y, z]: Vec, s: number): Vec => [x * s, y * s, z * s];

function direction(ra: number, dec = 0): Vec {
  const a = ra * rad, d = dec * rad;
  return [Math.cos(a) * Math.cos(d), Math.sin(d), Math.sin(a) * Math.cos(d)];
}

const forward = direction(48, 23);
const right = direction(138);
const up = direction(228, 67);
const equator = Array.from({ length: 121 }, (_, index) => scale(direction(index * 3), 1.42));
const nearEquator = Array.from({ length: 61 }, (_, index) => scale(direction(-42 + index * 3), 1.42));

function prepareRaster(ctx: CanvasRenderingContext2D, radius: number): Raster {
  const size = radius * 2;
  const pixels = ctx.createImageData(size, size);
  const longitude = new Float32Array(size * size);
  const latitude = new Float32Array(size * size);
  const light = new Float32Array(size * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const h = (x + 0.5 - radius) / radius;
      const v = (radius - y - 0.5) / radius;
      const distance = h * h + v * v;
      if (distance >= 1) continue;
      const depth = Math.sqrt(1 - distance);
      const world = add(add(scale(right, h), scale(up, v)), scale(forward, depth));
      const pixel = y * size + x;
      longitude[pixel] = Math.atan2(world[2], world[0]) / tau;
      latitude[pixel] = 0.5 - Math.asin(Math.max(-1, Math.min(1, world[1]))) / Math.PI;
      light[pixel] = 0.36 + 0.64 * Math.max(0, -h * 0.4 + v * 0.45 + depth * 0.8);
    }
  }
  return { pixels, radius, longitude, latitude, light };
}

const stars = Array.from({ length: 96 }, (_, index) => {
  const t = index + 1;
  return [turn(t * .6180339887), turn(t * .795438), turn(t * .327511)];
});

export function makeScene(canvas: HTMLCanvasElement, layout: "lab" | "orbital" = "lab") {
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  const layer = document.createElement("canvas");
  const layerCtx = layer.getContext("2d");
  if (!layerCtx) return null;
  let raster: Raster | undefined;
  let texture: ImageData | undefined;

  function setTexture(image: HTMLImageElement) {
    const source = document.createElement("canvas");
    source.width = image.naturalWidth;
    source.height = image.naturalHeight;
    const sourceCtx = source.getContext("2d");
    if (!sourceCtx) return;
    sourceCtx.drawImage(image, 0, 0);
    texture = sourceCtx.getImageData(0, 0, source.width, source.height);
  }

  function draw(width: number, height: number, ra: number, dec: number, time = 0) {
    if (!ctx || !layerCtx || width < 1 || height < 1) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const pixelWidth = Math.round(width * ratio);
    const pixelHeight = Math.round(height * ratio);
    if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
    if (canvas.height !== pixelHeight) canvas.height = pixelHeight;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.fillStyle = "#071619";
    ctx.fillRect(0, 0, width, height);
    for (const [x, y, strength] of stars) {
      ctx.fillStyle = `rgba(224,239,228,${.12 + strength * .38})`;
      ctx.fillRect(x * width, y * height, 1 + strength, 1 + strength);
    }

    const orbital = layout === "orbital";
    const narrow = width <= 760;
    const radius = orbital ? Math.min(height * .61, width * (narrow ? .40 : .32)) : Math.min(width, height) * .235;
    const cx = orbital ? -radius * (narrow ? .20 : .34) : width * .5;
    const cy = height * .51;
    const project = (p: Vec): Point => ({
      x: cx + radius * dot(p, right),
      y: cy - radius * dot(p, up),
      depth: dot(p, forward),
    });
    function line(points: Vec[], color: string, dashed = false, weight = 1, projection = project) {
      if (!ctx || points.length === 0) return;
      ctx.beginPath();
      points.forEach((vec, index) => {
        const { x, y } = projection(vec);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = color;
      ctx.lineWidth = weight;
      ctx.setLineDash(dashed ? [4, 5] : []);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    if (!orbital) {
      line(equator, "#657c71", true);
      line([[0, -1.57, 0], [0, 1.65, 0]], "#82988a", true);
    }

    const resolution = Math.max(8, Math.min(220, Math.round(radius * ratio)));
    if (raster?.radius !== resolution) {
      raster = prepareRaster(layerCtx, resolution);
      layer.width = layer.height = resolution * 2;
    }
    const { pixels, longitude, latitude, light } = raster;
    const data = pixels.data;
    // The orbital view includes an illustrative daily spin for the chosen UTC time.
    const rotation = ra / 360 + (orbital ? turn(time / 86_400_000 + .46) : 0);
    for (let i = 0; i < light.length; i++) {
      const shade = light[i];
      if (!shade) continue;
      const out = i * 4;
      const u = turn(longitude[i] + .5 - rotation);
      const v = latitude[i];
      if (texture) {
        const sample = (Math.min(texture.height - 1, Math.floor(v * texture.height)) * texture.width +
          Math.floor(u * texture.width)) * 4;
        data[out] = 9 + texture.data[sample] * shade * .9;
        data[out + 1] = 16 + texture.data[sample + 1] * shade * .94;
        data[out + 2] = 20 + texture.data[sample + 2] * shade;
      } else {
        const grid = Math.sin(u * tau * 12) ** 2 < .025 || Math.sin(v * Math.PI * 6) ** 2 < .025;
        data[out] = (grid ? 60 : 22) * shade;
        data[out + 1] = (grid ? 116 : 60) * shade;
        data[out + 2] = (grid ? 110 : 70) * shade;
      }
      data[out + 3] = 255;
    }
    layerCtx.putImageData(pixels, 0, 0);
    ctx.drawImage(layer, cx - radius, cy - radius, radius * 2, radius * 2);
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, tau);
    ctx.strokeStyle = "#647c82";
    ctx.stroke();

    if (orbital) {
      const marker = (t: number) => {
        const angle = (-63 + t * 126) * rad;
        return [cx + radius * 1.14 * Math.cos(angle), cy + radius * 1.14 * Math.sin(angle)] as const;
      };
      ctx.beginPath();
      for (let i = 0; i <= 90; i++) {
        const [x, y] = marker(i / 90);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "#a9977d";
      ctx.lineWidth = 1;
      ctx.stroke();
      for (const value of [0, 1, ra / 360]) {
        const [x, y] = marker(value);
        ctx.beginPath();
        ctx.arc(x, y, value === ra / 360 ? 5 : 2.5, 0, tau);
        ctx.fillStyle = "#eaa83a";
        ctx.fill();
      }
    } else {
      line(nearEquator, "#9eafa6");
      const arc = Array.from({ length: 121 }, (_, i) => scale(direction(ra * i / 120), 1.42));
      line(arc, "#eaa83a", false, 2);
      line(Array.from({ length: 41 }, (_, i) => scale(direction(ra, dec * i / 40), 1.42)), "#a8ccfa", false, 2);
      line([[0, 0, 0], [0, 1.65, 0]], "#92aa9b", true);
    }

    // The orbital layout presents Dec from the side so the tilt stays legible.
    const viewRA = orbital ? 109 : ra;
    const axis = direction(viewRA, dec);
    const side = direction(viewRA + 90);
    const vertical = direction(viewRA + 180, 90 - dec);
    const scopeScale = Math.min(width * (narrow ? .25 : .16), height * .39);
    const scopeX = width * (narrow ? .70 : .46);
    const scopeY = height * .52;
    const scopeProject = orbital ? (p: Vec): Point => {
      const relative = add(p, scale(axis, -1.49));
      return {
        x: scopeX + scopeScale * dot(relative, right),
        y: scopeY - scopeScale * dot(relative, up),
        depth: dot(relative, forward),
      };
    } : project;
    if (orbital) {
      ctx.beginPath();
      ctx.arc(scopeX, scopeY, scopeScale * .65, -1.25, 1.25);
      ctx.strokeStyle = "#8aa49f";
      ctx.setLineDash([4, 6]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    line(orbital ? [scale(axis, 1.19), scale(axis, 2.24)] : [[0, 0, 0], scale(axis, 1.94)],
      "#76c6b4", dot(axis, forward) < 0, 1.5, scopeProject);

    // Project the optical tube and solar panels from the same local axes.
    const rings = [1.30, 1.69].map((at, end) => Array.from({ length: 8 }, (_, i) =>
      add(scale(axis, at), add(scale(side, (orbital && end ? .20 : .115) * Math.cos(tau * i / 8)),
        scale(vertical, (orbital && end ? .20 : .115) * Math.sin(tau * i / 8)))),
    ));
    const faces = rings[0].map((point, i) => {
      const j = (i + 1) % 8;
      return { path: [point, rings[0][j], rings[1][j], rings[1][i]], fill: i % 2 ? "#667771" : "#c5d6cc" };
    });
    if (orbital) {
      for (const sign of [-1, 1]) {
        const panel = (a: number, b: number) => add(
          add(scale(axis, a), scale(side, b * sign)),
          scale(vertical, -.33 * b * sign + (a - 1.31) * .42),
        );
        faces.push({ path: [panel(1.31, .11), panel(1.50, .11), panel(1.50, .92), panel(1.31, .92)], fill: "#456365" });
        for (let cell = 0; cell < 5; cell++) {
          const edge = .17 + cell * .145;
          faces.push({ path: [panel(1.33, edge), panel(1.48, edge), panel(1.48, edge + .12), panel(1.33, edge + .12)], fill: "#597b80" });
        }
      }
    }
    faces.push({ path: rings[0], fill: "#607068" }, { path: rings[1], fill: "#1f362e" });
    faces.sort((a, b) => dot(a.path.reduce(add), forward) / a.path.length - dot(b.path.reduce(add), forward) / b.path.length);
    for (const { path, fill } of faces) {
      ctx.beginPath();
      path.forEach((point, i) => {
        const { x, y } = scopeProject(point);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.strokeStyle = "#d9eadf";
      ctx.lineWidth = .8;
      ctx.stroke();
    }

    const tip = scopeProject(scale(axis, orbital ? 2.24 : 1.94));
    ctx.beginPath();
    ctx.arc(tip.x, tip.y, 3.5, 0, tau);
    ctx.fillStyle = "#76c6b4";
    ctx.fill();
    if (!orbital) {
      const pole = project([0, 1.65, 0]);
      ctx.fillStyle = "#bfcfc5";
      ctx.font = "11px ui-monospace, monospace";
      ctx.textAlign = "center";
      ctx.fillText("NORTE", pole.x, pole.y - 7);
    }
  }

  return { draw, setTexture };
}
