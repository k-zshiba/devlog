import { cp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import yaml from 'js-yaml';

const require = createRequire(import.meta.url);

// Only YAML boolean true selects Marp. A typo must not silently publish an article.
function isSlide(text, filename) {
  const lines = text.replace(/^\uFEFF/, '').split(/\r?\n/);
  if (lines[0]?.trimEnd() !== '---') return false;
  const end = lines.findIndex((line, index) => index > 0 && line.trimEnd() === '---');
  if (end < 0) throw new Error(`${filename}: front matter has no closing ---`);
  let data;
  try {
    data = yaml.load(lines.slice(1, end).join('\n'), { schema: yaml.CORE_SCHEMA });
  } catch (error) {
    throw new Error(`${filename}: ${error.message}`);
  }
  if (data == null) return false;
  if (typeof data !== 'object' || Array.isArray(data)) {
    throw new Error(`${filename}: front matter must be a YAML mapping`);
  }
  if ('marp' in data && typeof data.marp !== 'boolean') {
    throw new Error(`${filename}: marp must be true or false (without quotes)`);
  }
  return data.marp === true;
}

export async function findSlides(source) {
  const slides = [];
  async function walk(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const filename = path.join(directory, entry.name);
      if (entry.isDirectory()) await walk(filename);
      else if (entry.isFile() && /\.(md|markdown)$/i.test(entry.name)) {
        if (isSlide(await readFile(filename, 'utf8'), filename)) {
          slides.push(path.relative(source, filename));
        }
      }
    }
  }
  await walk(source);
  return slides.sort();
}

export async function prepareContent(source = 'docs', staged = '.build/docs', baseurl) {
  const slides = await findSlides(source);
  // Work on a disposable copy so Jekyll cannot render a slide as an article.
  await rm(staged, { recursive: true, force: true });
  await mkdir(path.dirname(staged), { recursive: true });
  await cp(source, staged, { recursive: true });
  for (const slide of slides) await rm(path.join(staged, slide));
  if (baseurl !== undefined) {
    const configPath = path.join(staged, '_config.yml');
    const config = yaml.load(await readFile(configPath, 'utf8'), { schema: yaml.CORE_SCHEMA });
    config.baseurl = baseurl;
    await writeFile(configPath, yaml.dump(config));
  }
  return slides;
}

export async function buildSlides(source = 'docs', destination = '_site') {
  const slides = await findSlides(source);
  for (const slide of slides) {
    const output = path.join(destination, slide.replace(/\.(md|markdown)$/i, '.html'));
    // Existing output means a Jekyll page or static HTML already owns this URL.
    try {
      await readFile(output);
      throw new Error(`${slide}: output already exists: ${output}. Rebuild Jekyll first and check for URL collisions.`);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    await mkdir(path.dirname(output), { recursive: true });
    const result = spawnSync(process.execPath, [
      require.resolve('@marp-team/marp-cli/marp-cli.js'),
      '--no-config', '--no-stdin', path.join(source, slide), '--output', output,
    ], { stdio: ['ignore', 'inherit', 'inherit'] });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`Marp failed for ${slide} (exit ${result.status})`);
  }
  return slides;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  try {
    if (process.argv[2] === 'prepare') {
      const slides = await prepareContent('docs', '.build/docs', process.env.SITE_BASEURL);
      console.log(`Prepared .build/docs for Jekyll; ${slides.length} slide deck(s) excluded.`);
    } else if (process.argv[2] === 'slides') {
      const slides = await buildSlides();
      console.log(`Built ${slides.length} slide deck(s) into _site.`);
    } else {
      throw new Error('Usage: node scripts/build-content.mjs prepare|slides');
    }
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
