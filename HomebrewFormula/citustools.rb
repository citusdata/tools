class Docker < Requirement
  fatal true

  satisfy { which "docker" }

  def message
    "Docker is required. Get it at https://www.docker.com/docker-mac"
  end
end

class Citustools < Formula
  desc "Tools and config used in Citus Data projects."
  homepage "https://github.com/citusdata/tools"
  url "https://github.com/citusdata/tools/archive/v0.7.10.tar.gz"
  sha256 "3593ca42e3f388e78f4299699d93092c7ee672b3d090c2a9c219c624a4425d5c"

  depends_on "uncrustify"
  depends_on Docker

  def install
    # FIXME: ensure installdirs runs exactly once
    ENV.deparallelize

    system "make", "install", "prefix=#{prefix}", "sysconfdir=#{etc}"
  end

  test do
    system "true"
  end
end
